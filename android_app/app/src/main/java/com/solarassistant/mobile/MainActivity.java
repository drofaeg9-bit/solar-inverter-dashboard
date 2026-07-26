package com.solarassistant.mobile;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.DownloadManager;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.SslErrorHandler;
import android.webkit.URLUtil;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import java.net.URI;
import java.net.URISyntaxException;

public final class MainActivity extends Activity {
    private static final String PREFERENCES = "solar_invertor_mobile";
    private static final String SERVER_URL_KEY = "server_url";
    private static final String DEFAULT_SERVER_URL = "http://192.168.1.100:8080";
    private static final int STORAGE_PERMISSION_REQUEST = 41;

    private SharedPreferences preferences;
    private WebView webView;
    private ProgressBar progressBar;
    private LinearLayout errorPanel;
    private TextView errorMessage;
    private TextView addressLabel;
    private String serverUrl = "";
    private PendingDownload pendingDownload;

    private record PendingDownload(
            String url,
            String userAgent,
            String contentDisposition,
            String mimeType
    ) {}

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(15, 23, 42));
        getWindow().setNavigationBarColor(Color.rgb(2, 6, 23));
        preferences = getSharedPreferences(PREFERENCES, MODE_PRIVATE);
        createInterface();
        configureWebView();

        serverUrl = preferences.getString(SERVER_URL_KEY, "");
        if (serverUrl.isBlank()) {
            showServerDialog(true);
        } else {
            loadDashboard();
        }
    }

    private void createInterface() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(2, 6, 23));

        LinearLayout toolbar = new LinearLayout(this);
        toolbar.setGravity(Gravity.CENTER_VERTICAL);
        toolbar.setPadding(dp(4), dp(4), dp(4), dp(4));
        toolbar.setBackgroundColor(Color.rgb(15, 23, 42));
        root.addView(toolbar, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(52)));

        toolbar.addView(toolbarButton("\u2039", view -> goBack()));
        toolbar.addView(toolbarButton("\u21bb", view -> webView.reload()));
        toolbar.addView(toolbarButton("\u2302", view -> loadDashboard()));

        addressLabel = new TextView(this);
        addressLabel.setTextColor(Color.rgb(148, 163, 184));
        addressLabel.setTextSize(12);
        addressLabel.setSingleLine(true);
        addressLabel.setGravity(Gravity.CENTER_VERTICAL);
        addressLabel.setPadding(dp(8), 0, dp(8), 0);
        toolbar.addView(addressLabel, new LinearLayout.LayoutParams(0, dp(44), 1));
        toolbar.addView(toolbarButton("\u2699", view -> showServerDialog(false)));

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        root.addView(progressBar, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(3)));

        FrameLayout content = new FrameLayout(this);
        root.addView(content, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(2, 6, 23));
        content.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        errorPanel = new LinearLayout(this);
        errorPanel.setOrientation(LinearLayout.VERTICAL);
        errorPanel.setGravity(Gravity.CENTER);
        errorPanel.setPadding(dp(28), dp(28), dp(28), dp(28));
        errorPanel.setBackgroundColor(Color.rgb(2, 6, 23));
        errorPanel.setVisibility(View.GONE);

        TextView errorTitle = new TextView(this);
        errorTitle.setText(R.string.dashboard_unavailable);
        errorTitle.setTextColor(Color.WHITE);
        errorTitle.setTextSize(22);
        errorTitle.setGravity(Gravity.CENTER);
        errorPanel.addView(errorTitle);

        errorMessage = new TextView(this);
        errorMessage.setTextColor(Color.rgb(148, 163, 184));
        errorMessage.setTextSize(14);
        errorMessage.setGravity(Gravity.CENTER);
        errorMessage.setPadding(0, dp(10), 0, dp(18));
        errorPanel.addView(errorMessage);

        LinearLayout errorActions = new LinearLayout(this);
        errorActions.setGravity(Gravity.CENTER);
        errorActions.addView(actionButton("Retry", view -> loadDashboard()));
        errorActions.addView(actionButton("Server URL", view -> showServerDialog(false)));
        errorPanel.addView(errorActions);

        content.addView(errorPanel, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(root);
    }

    private Button toolbarButton(String label, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextColor(Color.WHITE);
        button.setTextSize(21);
        button.setAllCaps(false);
        button.setMinWidth(0);
        button.setMinimumWidth(0);
        button.setPadding(0, 0, 0, 0);
        button.setBackgroundColor(Color.TRANSPARENT);
        button.setOnClickListener(listener);
        button.setContentDescription(label);
        button.setLayoutParams(new LinearLayout.LayoutParams(dp(44), dp(44)));
        return button;
    }

    private Button actionButton(String label, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextColor(Color.rgb(6, 32, 42));
        button.setBackgroundColor(Color.rgb(34, 211, 238));
        button.setOnClickListener(listener);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, dp(48));
        params.setMargins(dp(5), 0, dp(5), 0);
        button.setLayoutParams(params);
        return button;
    }

    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setMediaPlaybackRequiresUserGesture(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setUserAgentString(settings.getUserAgentString() + " SolarInvertorAndroid/1.0");
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, false);

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int progress) {
                progressBar.setProgress(progress);
                progressBar.setVisibility(progress >= 100 ? View.GONE : View.VISIBLE);
            }
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                errorPanel.setVisibility(View.GONE);
                webView.setVisibility(View.VISIBLE);
                addressLabel.setText(Uri.parse(url).getHost());
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme();
                if ("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme)) {
                    return false;
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (ActivityNotFoundException error) {
                    Toast.makeText(MainActivity.this, "No app can open this link", Toast.LENGTH_SHORT).show();
                }
                return true;
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    showLoadError(error.getDescription().toString());
                }
            }

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse response) {
                if (request.isForMainFrame() && response.getStatusCode() >= 400) {
                    showLoadError("HTTP " + response.getStatusCode());
                }
            }

            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, android.net.http.SslError error) {
                handler.cancel();
                showLoadError("The server certificate is not trusted");
            }
        });

        webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) ->
                requestDownload(new PendingDownload(url, userAgent, contentDisposition, mimeType)));
    }

    private void loadDashboard() {
        if (serverUrl.isBlank()) {
            showServerDialog(true);
            return;
        }
        errorPanel.setVisibility(View.GONE);
        webView.setVisibility(View.VISIBLE);
        addressLabel.setText(Uri.parse(serverUrl).getHost());
        webView.loadUrl(serverUrl);
    }

    private void showServerDialog(boolean required) {
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setText(serverUrl.isBlank() ? DEFAULT_SERVER_URL : serverUrl);
        input.setSelection(input.getText().length());
        input.setHint("http://192.168.1.100:8080");
        int padding = dp(22);
        FrameLayout container = new FrameLayout(this);
        container.setPadding(padding, 0, padding, 0);
        container.addView(input, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Solar Invertor server")
                .setMessage("Enter the dashboard address reachable from this phone. Use a LAN IP or Tailscale address.")
                .setView(container)
                .setPositiveButton("Connect", null)
                .setNegativeButton(required ? null : "Cancel", null)
                .create();
        dialog.setCanceledOnTouchOutside(!required);
        dialog.setCancelable(!required);
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener(view -> {
                    String normalized = normalizeServerUrl(input.getText().toString());
                    if (normalized == null) {
                        input.setError("Enter a valid http:// or https:// address");
                        return;
                    }
                    serverUrl = normalized;
                    preferences.edit().putString(SERVER_URL_KEY, serverUrl).apply();
                    dialog.dismiss();
                    loadDashboard();
                }));
        dialog.show();
    }

    private String normalizeServerUrl(String value) {
        String normalized = value.trim();
        if (!normalized.contains("://")) {
            normalized = "http://" + normalized;
        }
        while (normalized.endsWith("/")) {
            normalized = normalized.substring(0, normalized.length() - 1);
        }
        try {
            URI uri = new URI(normalized);
            if (!("http".equalsIgnoreCase(uri.getScheme()) || "https".equalsIgnoreCase(uri.getScheme()))
                    || uri.getHost() == null) {
                return null;
            }
            return uri.toString();
        } catch (URISyntaxException error) {
            return null;
        }
    }

    private void showLoadError(String detail) {
        webView.setVisibility(View.GONE);
        errorMessage.setText(getString(R.string.load_error_details, detail, serverUrl));
        errorPanel.setVisibility(View.VISIBLE);
        progressBar.setVisibility(View.GONE);
    }

    private void requestDownload(PendingDownload download) {
        if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P
                && checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
            pendingDownload = download;
            requestPermissions(new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE}, STORAGE_PERMISSION_REQUEST);
            return;
        }
        enqueueDownload(download);
    }

    private void enqueueDownload(PendingDownload download) {
        try {
            String fileName = URLUtil.guessFileName(
                    download.url(), download.contentDisposition(), download.mimeType());
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(download.url()));
            request.setTitle(fileName);
            request.setMimeType(download.mimeType());
            request.setNotificationVisibility(
                    DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName);
            String cookie = CookieManager.getInstance().getCookie(download.url());
            if (cookie != null) request.addRequestHeader("Cookie", cookie);
            if (download.userAgent() != null) request.addRequestHeader("User-Agent", download.userAgent());
            DownloadManager manager = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
            manager.enqueue(request);
            Toast.makeText(this, "Downloading " + fileName, Toast.LENGTH_LONG).show();
        } catch (RuntimeException error) {
            Toast.makeText(this, "Download failed: " + error.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == STORAGE_PERMISSION_REQUEST && pendingDownload != null) {
            PendingDownload download = pendingDownload;
            pendingDownload = null;
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                enqueueDownload(download);
            } else {
                Toast.makeText(this, "Storage permission is required to save the CSV", Toast.LENGTH_LONG).show();
            }
        }
    }

    private void goBack() {
        if (webView.canGoBack()) webView.goBack(); else moveTaskToBack(true);
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) webView.goBack(); else super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        webView.stopLoading();
        webView.setWebChromeClient(null);
        webView.setWebViewClient(null);
        webView.destroy();
        super.onDestroy();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
