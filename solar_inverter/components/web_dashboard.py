from __future__ import annotations
import csv
import gzip
import json
import os
import secrets
import subprocess
import sys
import threading
import urllib.request
import urllib.error
from urllib.parse import parse_qs
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from pathlib import Path
from ..services import inverter_service
from ..services.inverter_service import *
from ..services.inverter_service_runtime import get_server_logs, get_updater_archive, get_updater_history
from .api_localization import SUPPORTED_API_LANGUAGES, localize_api_status
from .api_localization import localize_api_text, register_description, resolve_api_language
from .dashboard_template import ASSET_VERSION, WEB_DASHBOARD, WEB_ROOT
from .state_consistency import effective_battery_soc
DASHBOARD_INSTANCE_ID = f"{ASSET_VERSION}-{secrets.token_hex(8)}"
GIT_PATH = r"C:\Program Files\Git\bin\git.exe"
def check_git_available() -> tuple[bool, str]:
    """Check if git is available. Returns (is_available, path_or_error)."""
    import shutil
    if Path(GIT_PATH).exists():
        return True, GIT_PATH
    # Try to find git in PATH
    git_path = shutil.which("git")
    if git_path:
        return True, git_path
    return False, "Git not found"
def install_git() -> tuple[bool, str]:
    """Attempt to install git using winget on Windows. Returns (success, message)."""
    try:
        result = subprocess.run(
            ["winget", "install", "--id", "Git.Git", "-e", "--silent"],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            return True, "Git installed successfully"
        else:
            return False, f"Installation failed: {result.stderr}"
    except FileNotFoundError:
        return False, "winget not found. Please install Git manually from https://git-scm.com/download/win"
    except subprocess.TimeoutExpired:
        return False, "Installation timed out"
    except Exception as e:
        return False, f"Installation error: {str(e)}"


def github_update_status() -> dict[str, Any]:
    """Compare a bundled source commit with GitHub without requiring .git locally."""
    try:
        metadata = json.loads(
            (PROJECT_ROOT / ".solar-dashboard-upstream.json").read_text(encoding="utf-8")
        )
        repository = str(metadata["repository"])
        branch = str(metadata.get("branch") or "main")
        local_hash = str(metadata["commit"])
        if len(local_hash) != 40 or any(character not in "0123456789abcdef" for character in local_hash.lower()):
            raise ValueError("The bundled source commit is unavailable")

        def github_api(path: str) -> dict[str, Any]:
            request = urllib.request.Request(
                f"https://api.github.com/repos/{repository}/{path}",
                headers={"Accept": "application/vnd.github+json", "User-Agent": "solar-inverter-dashboard"},
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))

        latest = github_api(f"commits/{branch}")
        remote_hash = str(latest["sha"])
        remote_commit = latest["commit"]
        ahead = 0
        behind = 0
        if local_hash != remote_hash:
            comparison = github_api(f"compare/{local_hash}...{branch}")
            ahead = int(comparison.get("behind_by", 0))
            behind = int(comparison.get("ahead_by", 0))
        return {
            "available": True,
            "dashboard_version": ASSET_VERSION,
            "branch": branch,
            "local": {
                "hash": local_hash, "subject": str(metadata.get("message") or "Bundled update"),
                "date": str(metadata.get("committed_at") or ""),
            },
            "remote": {
                "hash": remote_hash, "subject": str(remote_commit.get("message", "")).split("\n", 1)[0],
                "date": str(remote_commit.get("author", {}).get("date", "")),
            },
            "ahead": ahead,
            "behind": behind,
        }
    except (KeyError, OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError) as error:
        return {"available": False, "error": str(error)}
DASHBOARD_IMAGE_PATHS = {
    "/assets/generator-mask.png": PROJECT_ROOT / "generator-mask.png",
    "/assets/grid.png": PROJECT_ROOT / "1258380.png",
    "/assets/inverter.svg": PROJECT_ROOT / "inverter.svg",
    "/assets/home.svg": PROJECT_ROOT / "home.svg",
}
DASHBOARD_STATIC_PATHS = {
    f"/static/{path.relative_to(WEB_ROOT).as_posix()}": path
    for path in WEB_ROOT.rglob("*")
    if path.is_file() and path.name != "index.html"
}
def web_state(language: str = "uk") -> dict[str, Any]:
    """Return a JSON-safe snapshot for the browser."""
    language = language if language in SUPPORTED_API_LANGUAGES else "uk"
    with state_lock:
        snapshot = dict(state)
        values = dict(state["values"])
    def effective_value(register: int) -> float | None:
        manual_value = manual_register_value(register)
        if manual_value is not None:
            return manual_value
        if register not in values:
            return None
        return normalize(register, values[register])[3]

    battery_current_value: float | None = None
    battery_current_value = effective_value(130)
    def battery_power_with_current_direction(value: float | None) -> float | None:
        """Use positive charge and negative discharge consistently for R134."""
        if value is None or battery_current_value is None or abs(battery_current_value) < 0.3:
            return value
        return abs(value) if battery_current_value > 0 else -abs(value)
    meters = []
    for register, fallbacks, label, minimum, maximum, unit in METER_DEFINITIONS:
        value = None
        source = ""
        for candidate in [register, *fallbacks]:
            value = effective_value(candidate)
            if value is not None:
                source = f"R{candidate}" + (" (manual)" if manual_register_value(candidate) is not None else "")
                break
        metadata_override = register_override(register)
        label = str(metadata_override.get("name", label))
        unit = str(metadata_override.get("unit", unit))
        if register == 134:
            value = battery_power_with_current_direction(value)
        elif register == 133:
            value = effective_battery_soc(value, None)
        available = value is not None
        if value is None:
            value = 0.0
            source = "Немає даних mbpoll"
        meters.append({
            "register": register,
            "label": localize_api_text(label, language),
            "label_source": label,
            "minimum": minimum,
            "maximum": maximum,
            "unit": unit,
            "value": value,
            "source": localize_api_text(source, language),
            "source_source": source,
            "available": available,
        })
    registers = []
    all_registers = KNOWN_REGISTERS
    for register in all_registers:
        raw = values.get(register)
        name, scale, unit, signed, group = register_metadata(register)
        edit = manual_register_edit(register)
        name = str(edit.get("name", name))
        unit = str(edit.get("unit", unit))
        group = str(edit.get("group", group))
        manual_value = manual_register_value(register)
        normalized_value = manual_value
        if manual_value is not None:
            display = f"{manual_value:g}"
        elif raw is None:
            display = "—"
        else:
            name, display, unit, normalized_value, group = normalize(register, raw)
            if register == 134:
                normalized_value = battery_power_with_current_direction(normalized_value)
                if normalized_value is not None:
                    display = str(int(normalized_value))
        registers.append({
            "register": register,
            "group": localize_api_text(group, language),
            "group_source": group,
            "name": localize_api_text(name, language),
            "name_source": name,
            "description": str(edit.get("description", register_description(register, name, unit, scale, signed, language))),
            "description_source": str(edit.get("description", register_description(register, name, unit, scale, signed, "uk"))),
            "display": localize_api_text(display, language),
            "display_source": display,
            "value": normalized_value,
            "unit": unit,
            "scale": scale,
            "signed": signed,
            "read_only": True, "maintenance": register in MAINTENANCE_REGISTERS, "word_format": "h_l" if REGISTER_WORD_FORMAT.get(register) else "word",
            "raw": raw,
            "available": manual_value is not None or raw is not None,
            "manual": manual_value is not None,
            "edited": bool(edit),
        })
    return {"language": language,
        "dashboard_version": ASSET_VERSION,
        "dashboard_instance": DASHBOARD_INSTANCE_ID,
        "online": bool(snapshot["online"]),
        "updated_at": snapshot["updated_at"],
        "cycle_seconds": snapshot["cycle_seconds"],
        "read_seconds": snapshot["read_seconds"],
        "cycle_id": snapshot["cycle_id"],
        "poll_rate_index": snapshot["poll_rate_index"],
        "read_mode": snapshot["read_mode"],
        "requests": snapshot["requests"],
        "successful": snapshot["successful"],
        "failed": snapshot["ошибок"],
        "error": localize_api_text(snapshot["error"], language),
        "error_source": snapshot["error"],
        "identifier": snapshot["identifier"],
        "paused": bool(snapshot["paused"]),
        "site_visits": inverter_service.site_visit_total,
        "site_visits_date": datetime.now(MADRID_TIME_ZONE).strftime("%d.%m.%Y"),
        "solar_energy": localize_api_status(solar_energy_summary(), language),
        "register_log": localize_api_status(register_log_status(), language),
        "register_map": localize_api_status(register_map_status(), language),
        "meters": meters,
        "registers": registers,
    }
def safe_console_print(message: str) -> None:
    """Print localized text without failing on a legacy Windows code page."""
    console_encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe_message = message.encode(
        console_encoding, errors="backslashreplace"
    ).decode(console_encoding)
    print(safe_message, flush=True)
def log_visit_to_console(
    handler: BaseHTTPRequestHandler, new_visitor: bool
) -> None:
    """Write request details to the private server terminal only."""
    peer = str(handler.client_address[0])
    forwarded = handler.headers.get("X-Forwarded-For", "")
    source = (
        forwarded.split(",", 1)[0].strip()
        if peer in {"127.0.0.1", "::1"} and forwarded
        else peer
    )
    details = {
        "подія": "відвідування_панелі",
        "дата": datetime.now(MADRID_TIME_ZONE).isoformat(timespec="seconds"),
        "усього_відвідувачів": inverter_service.site_visit_total,
        "новий_відвідувач": new_visitor,
        "джерело": source[:100],
        "ідентифікатор": (
            handler.headers.get("Tailscale-User-Login")
            or handler.headers.get("Tailscale-User-Name")
            or "публічний/анонімний"
        )[:160],
        "джерело_переходу": handler.headers.get("Referer", "прямий перехід")[:500],
        "браузер": handler.headers.get("User-Agent", "невідомо")[:500],
    }
    message = (
        "[Web Dashboard] VISITOR "
        + json.dumps(details, ensure_ascii=False, separators=(",", ":"))
    )
    safe_console_print(message)
class DashboardHandler(BaseHTTPRequestHandler):
    """Serve the dashboard and its small JSON API."""

    def send_content(
        self,
        body: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: dict[str, str] | None = None,
        *,
        cache_control: str = "no-store",
        etag: str | None = None,
        compress: bool = False,
    ) -> None:
        try:
            if etag and self.headers.get("If-None-Match") == etag:
                self.send_response(HTTPStatus.NOT_MODIFIED)
                self.send_header("Cache-Control", cache_control)
                self.send_header("ETag", etag)
                self.end_headers()
                return
            response_headers = dict(extra_headers or {})
            if (
                compress
                and len(body) >= 1024
                and "gzip" in self.headers.get("Accept-Encoding", "").lower()
            ):
                body = gzip.compress(body, compresslevel=5, mtime=0)
                response_headers["Content-Encoding"] = "gzip"
                vary = response_headers.get("Vary", "")
                response_headers["Vary"] = ", ".join(
                    item for item in (vary, "Accept-Encoding") if item
                )
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache_control)
            if etag:
                self.send_header("ETag", etag)
            for name, value in response_headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            # Browsers and reverse proxies may cancel an obsolete polling request.
            return

    def do_GET(self) -> None:
        request_path = self.path.split("?", 1)[0]
        query = parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
        language = resolve_api_language(
            query.get("lang", [""])[0], self.headers.get("Accept-Language", "")
        )
        if request_path in DASHBOARD_STATIC_PATHS:
            path = DASHBOARD_STATIC_PATHS[request_path]
            content_type = (
                "text/css; charset=utf-8"
                if path.suffix.lower() == ".css"
                else "text/javascript; charset=utf-8"
            )
            try:
                metadata = path.stat()
                self.send_content(
                    path.read_bytes(),
                    content_type,
                    cache_control="public, max-age=31536000, immutable",
                    etag=f'W/"{metadata.st_mtime_ns:x}-{metadata.st_size:x}"',
                    compress=True,
                )
            except OSError:
                self.send_content(b"", content_type, HTTPStatus.NOT_FOUND)
            return
        if request_path in DASHBOARD_IMAGE_PATHS:
            try:
                image_path = DASHBOARD_IMAGE_PATHS[request_path]
                metadata = image_path.stat()
                content_type = (
                    "image/svg+xml"
                    if image_path.suffix.lower() == ".svg"
                    else "image/png"
                )
                self.send_content(
                    image_path.read_bytes(),
                    content_type,
                    cache_control="public, max-age=31536000, immutable",
                    etag=f'W/"{metadata.st_mtime_ns:x}-{metadata.st_size:x}"',
                    compress=image_path.suffix.lower() == ".svg",
                )
            except OSError:
                self.send_content(b"", content_type, HTTPStatus.NOT_FOUND)
            return
        if request_path in {"/favicon.png", "/favicon.ico"}:
            try:
                metadata = FAVICON_PATH.stat()
                self.send_content(
                    FAVICON_PATH.read_bytes(),
                    "image/png",
                    cache_control="public, max-age=31536000, immutable",
                    etag=f'W/"{metadata.st_mtime_ns:x}-{metadata.st_size:x}"',
                )
            except OSError:
                self.send_content(b"", "image/png", HTTPStatus.NOT_FOUND)
            return

        if request_path == "/":
            print(f"[Web Dashboard] GET / - Serving main page")
            new_visitor = not visitor_was_counted(
                self.headers.get("Cookie", "")
            )
            if new_visitor:
                increment_site_visits()
            log_visit_to_console(self, new_visitor)
            initial_state = json.dumps(
                web_state(language), ensure_ascii=False, separators=(",", ":")
            ).replace("<", "\\u003c")
            page = WEB_DASHBOARD.replace(
                "/*__INITIAL_STATE__*/null", initial_state, 1
            )
            response_headers: dict[str, str] = {}
            if new_visitor:
                cookie = (
                    f"{COUNTED_VISITOR_COOKIE}=1; Path=/; Max-Age=31536000; "
                    "HttpOnly; SameSite=Lax"
                )
                if (
                    self.headers.get("X-Forwarded-Proto", "").lower() == "https"
                    or self.headers.get("Host", "").endswith(".ts.net")
                ):
                    cookie += "; Secure"
                response_headers["Set-Cookie"] = cookie
            self.send_content(
                page.encode("utf-8"),
                "text/html; charset=utf-8",
                extra_headers=response_headers,
                cache_control="no-store, no-cache, must-revalidate",
                compress=True,
            )
            return
        if request_path == "/api/version":
            body = json.dumps({"dashboard_version": ASSET_VERSION, "dashboard_instance": DASHBOARD_INSTANCE_ID}).encode("utf-8")
            self.send_content(body, "application/json; charset=utf-8")
            return
        if request_path == "/api/updater-history/download":
            archive = get_updater_archive(query.get("file", [""])[0])
            if archive is None:
                self.send_content(b"Updater archive not found", "text/plain; charset=utf-8",
                                  HTTPStatus.NOT_FOUND)
                return
            headers = {"Content-Disposition": f'attachment; filename="{archive.name}"'}
            self.send_content(archive.read_bytes(), "application/vnd.python.pyz",
                              extra_headers=headers, cache_control="private, no-store")
            return
        if request_path == "/api/state":
            print(f"[Web Dashboard] API /api/state - Serving state snapshot")
            body = json.dumps(web_state(language), ensure_ascii=False).encode("utf-8")
            self.send_content(
                body,
                "application/json; charset=utf-8",
                extra_headers={
                    "Content-Language": language,
                    "Vary": "Accept-Language",
                },
                compress=True,
            )
            return
        if request_path == "/api/logs":
            print(f"[Web Dashboard] API /api/logs - Serving server logs")
            body = json.dumps(get_server_logs(), ensure_ascii=False).encode("utf-8")
            self.send_content(body, "application/json; charset=utf-8")
            return
        if request_path == "/api/historical":
            period = query.get("period", ["realtime"])[0]
            print(f"[Web Dashboard] API /api/historical - Period: {period}")
            body = json.dumps(get_chart_history(period), ensure_ascii=False).encode("utf-8")
            self.send_content(body, "application/json; charset=utf-8")
            return
        if request_path == "/api/git/commits":
            print(f"[Web Dashboard] API /api/git/commits - Fetching git commit history")
            try:
                # Check git availability and get path
                is_available, git_path = check_git_available()
                if not is_available:
                    body = json.dumps({"error": git_path}, ensure_ascii=False).encode("utf-8")
                    self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

                # Use %% to escape % on Windows PowerShell
                result = subprocess.run(
                    [git_path, "log", "--pretty=format:%H%%ai%%s", "--date=iso", "-20"],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                print(f"[Web Dashboard] Git log result: returncode={result.returncode}, stderr={result.stderr}")
                if result.returncode != 0:
                    body = json.dumps({"error": f"Failed to fetch git history: {result.stderr}"}, ensure_ascii=False).encode("utf-8")
                    self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

                commits = []
                for line in result.stdout.strip().split("\n") if result.stdout.strip() else []:
                    parts = line.split("|", 2)
                    if len(parts) == 3:
                        commits.append({
                            "hash": parts[0],
                            "date": parts[1],
                            "message": parts[2]
                        })

                body = json.dumps({"commits": commits}, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8")
            except subprocess.TimeoutExpired:
                body = json.dumps({"error": "Git command timed out"}, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", HTTPStatus.REQUEST_TIMEOUT)
            except Exception as e:
                print(f"[Web Dashboard] Git commits error: {e}")
                body = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if request_path.startswith("/api/git/download-bundle"):
            filename = query.get("filename", ["solar-dashboard-update.pyz"])[0]
            if Path(filename).name != filename or not filename.endswith(".pyz"):
                body = json.dumps({"error": "Invalid bundle filename"}).encode("utf-8")
                self.send_content(
                    body,
                    "application/json; charset=utf-8",
                    HTTPStatus.BAD_REQUEST,
                )
                return
            bundle_path = PROJECT_ROOT / "deploy" / filename
            print(f"[Web Dashboard] API /api/git/download-bundle - Serving: {bundle_path}")

            if not bundle_path.exists():
                body = json.dumps({"error": "Bundle file not found"}, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", HTTPStatus.NOT_FOUND)
                return

            try:
                self.send_content(
                    bundle_path.read_bytes(),
                    "application/octet-stream",
                    extra_headers={
                        "Content-Disposition": f'attachment; filename="{filename}"'
                    },
                )
            except OSError as error:
                body = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if request_path == "/api/updater-history":
            print("[Web Dashboard] API /api/updater-history - Fetching updater history and GitHub status")
            try:
                history = get_updater_history()
                github_status = github_update_status()
                body = json.dumps(
                    {"history": history, "github_status": github_status}, ensure_ascii=False
                ).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8")
            except Exception as e:
                print(f"[Web Dashboard] Updater history error: {e}")
                body = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if request_path == "/api/git/check":
            print(f"[Web Dashboard] API /api/git/check - Checking git availability")
            is_available, path_or_error = check_git_available()
            body = json.dumps({"available": is_available, "path": path_or_error if is_available else None, "error": path_or_error if not is_available else None}, ensure_ascii=False).encode("utf-8")
            self.send_content(body, "application/json; charset=utf-8")
            return
        if request_path == "/api/register-log/download":
            with inverter_service.register_log_lock:
                path = inverter_service.register_log_path
                if path is None and REGISTER_LOG_DIRECTORY.exists():
                    path = max(
                        REGISTER_LOG_DIRECTORY.glob("register_changes_*.csv"),
                        key=lambda candidate: candidate.stat().st_mtime,
                        default=None,
                    )
                if inverter_service.register_log_file is not None:
                    inverter_service.register_log_file.flush()
            if path is None or not path.exists():
                self.send_content(
                    '{"error":"журнал ще не створено"}'.encode("utf-8"),
                    "application/json; charset=utf-8",
                    HTTPStatus.NOT_FOUND,
                )
                return
            try:
                self.send_content(
                    path.read_bytes(),
                    "text/csv; charset=utf-8",
                    extra_headers={
                        "Content-Disposition": f'attachment; filename="{path.name}"'
                    },
                )
            except OSError as error:
                body = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_content(
                    body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR
                )
            return
        self.send_content(
            '{"error":"не знайдено"}'.encode("utf-8"),
            "application/json",
            HTTPStatus.NOT_FOUND,
        )

    def do_POST(self) -> None:
        if self.path == "/api/manual-register-value":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                register = int(payload.get("register"))
                clear = bool(payload.get("clear"))
                fields = payload.get("fields")
                if fields is not None and not isinstance(fields, dict):
                    raise ValueError("fields must be an object")
                result = (
                    set_manual_register_edit(register, fields, clear_value=clear)
                    if fields is not None
                    else set_manual_register_value(register, None if clear else payload.get("value"))
                )
                body = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8")
            except (TypeError, ValueError, OSError, json.JSONDecodeError) as error:
                body = json.dumps({"error": str(error)}, ensure_ascii=False).encode("utf-8")
                self.send_content(
                    body, "application/json; charset=utf-8", HTTPStatus.BAD_REQUEST
                )
            return

        if self.path == "/api/register-map":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0:
                    raise ValueError("CSV file is empty")
                if length > REGISTER_MAP_MAX_BYTES:
                    raise ValueError("CSV file is larger than 1 MiB")
                print(f"[Web Dashboard] API /api/register-map - Uploading CSV, size: {length} bytes")
                result = replace_register_map(self.rfile.read(length))
                body = json.dumps(result, ensure_ascii=False).encode("utf-8")
                print(f"[Web Dashboard] API /api/register-map - Result: {result.get('error') or 'success'}")
                self.send_content(body, "application/json; charset=utf-8")
            except (ValueError, OSError, csv.Error) as error:
                print(f"[Web Dashboard] API /api/register-map - Error: {error}")
                body = json.dumps({"error": str(error)}, ensure_ascii=False).encode("utf-8")
                self.send_content(
                    body, "application/json; charset=utf-8", HTTPStatus.BAD_REQUEST
                )
            return

        if self.path == "/api/git/checkout-and-build":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                commit = payload.get("commit")
                print(f"[Web Dashboard] API /api/git/checkout-and-build - Commit: {commit}")

                # Check git availability and get path
                is_available, git_path = check_git_available()
                if not is_available:
                    body = json.dumps({"error": git_path}, ensure_ascii=False).encode("utf-8")
                    self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

                # Checkout the commit
                checkout_result = subprocess.run(
                    [git_path, "checkout", commit],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if checkout_result.returncode != 0:
                    body = json.dumps({"error": f"Checkout failed: {checkout_result.stderr}"}, ensure_ascii=False).encode("utf-8")
                    self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

                # Build the update bundle
                build_result = subprocess.run(
                    ["py", "-3", "deploy/build_update_bundle.py"],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if build_result.returncode != 0:
                    body = json.dumps({"error": f"Build failed: {build_result.stderr}"}, ensure_ascii=False).encode("utf-8")
                    self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

                # Find the generated bundle
                bundle_path = PROJECT_ROOT / "deploy" / "solar-dashboard-update.pyz"
                if not bundle_path.exists():
                    body = json.dumps({"error": "Bundle file not found after build"}, ensure_ascii=False).encode("utf-8")
                    self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

                # Get commit info for database
                log_result = subprocess.run(
                    [git_path, "log", "-1", "--pretty=format:%s%%ai", commit],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                commit_message = ""
                commit_date = ""
                if log_result.returncode == 0:
                    parts = log_result.stdout.split("|", 1)
                    if len(parts) == 2:
                        commit_message = parts[0]
                        commit_date = parts[1]

                # Capture build output for database
                build_output = build_result.stdout.strip() if build_result.stdout else ""

                # Record to database
                record_updater_version(commit, commit_message, commit_date, "local", str(bundle_path), build_output)

                body = json.dumps({
                    "success": True,
                    "bundlePath": str(bundle_path),
                    "downloadUrl": f"/api/git/download-bundle?filename={bundle_path.name}"
                }, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8")

            except subprocess.TimeoutExpired:
                body = json.dumps({"error": "Git operation timed out"}, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", HTTPStatus.REQUEST_TIMEOUT)
            except Exception as e:
                body = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/git/download-from-github":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                commit = payload.get("commit")
                token = payload.get("token")
                repo_url = payload.get("repo_url")
                print(f"[Web Dashboard] API /api/git/download-from-github - Commit: {commit}, Repo: {repo_url}")

                # Parse GitHub repo from provided URL or use git remote
                if repo_url:
                    # Parse repo from provided URL
                    if repo_url.startswith("https://github.com/"):
                        repo_path = repo_url.replace("https://github.com/", "").replace(".git", "")
                    elif repo_url.startswith("git@github.com:"):
                        repo_path = repo_url.replace("git@github.com:", "").replace(".git", "")
                    else:
                        body = json.dumps({"error": f"Invalid GitHub URL format: {repo_url}"}, ensure_ascii=False).encode("utf-8")
                        self.send_content(body, "application/json; charset=utf-8", HTTPStatus.BAD_REQUEST)
                        return
                else:
                    # Check git availability and get path
                    is_available, git_path = check_git_available()
                    if not is_available:
                        body = json.dumps({"error": git_path}, ensure_ascii=False).encode("utf-8")
                        self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
                        return

                    # Get GitHub repo info from git remote
                    remote_result = subprocess.run(
                        [git_path, "remote", "get-url", "origin"],
                        cwd=PROJECT_ROOT,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if remote_result.returncode != 0:
                        body = json.dumps({"error": "Failed to get git remote URL"}, ensure_ascii=False).encode("utf-8")
                        self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
                        return

                    remote_url = remote_result.stdout.strip()
                    # Parse GitHub repo from URL (supports both https and git@ formats)
                    if remote_url.startswith("https://github.com/"):
                        repo_path = remote_url.replace("https://github.com/", "").replace(".git", "")
                    elif remote_url.startswith("git@github.com:"):
                        repo_path = remote_url.replace("git@github.com:", "").replace(".git", "")
                    else:
                        body = json.dumps({"error": f"Unsupported git remote: {remote_url}"}, ensure_ascii=False).encode("utf-8")
                        self.send_content(body, "application/json; charset=utf-8", HTTPStatus.BAD_REQUEST)
                        return

                # Try to download from GitHub releases
                # First, try to find a release tag matching the commit
                api_url = f"https://api.github.com/repos/{repo_path}/releases"
                headers = {}
                if token:
                    headers["Authorization"] = f"token {token}"

                req = urllib.request.Request(api_url, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=10) as response:
                        releases = json.loads(response.read().decode())

                    # Look for release with this commit
                    for release in releases:
                        if commit in release.get("target_commitish", ""):
                            # Download the asset
                            for asset in release.get("assets", []):
                                if asset["name"] == "solar-dashboard-update.pyz":
                                    download_url = asset["browser_download_url"]
                                    bundle_path = PROJECT_ROOT / "deploy" / "solar-dashboard-update.pyz"

                                    download_req = urllib.request.Request(download_url, headers=headers)
                                    with urllib.request.urlopen(download_req, timeout=30) as dl_response:
                                        bundle_path.write_bytes(dl_response.read())

                                    # Get commit info for database
                                    log_result = subprocess.run(
                                        [git_path, "log", "-1", "--pretty=format:%s%%ai", commit],
                                        cwd=PROJECT_ROOT,
                                        capture_output=True,
                                        text=True,
                                        timeout=10
                                    )
                                    commit_message = ""
                                    commit_date = ""
                                    if log_result.returncode == 0:
                                        parts = log_result.stdout.split("|", 1)
                                        if len(parts) == 2:
                                            commit_message = parts[0]
                                            commit_date = parts[1]

                                    # Record to database
                                    record_updater_version(commit, commit_message, commit_date, "github", str(bundle_path), f"Downloaded from GitHub: {asset['name']}")

                                    body = json.dumps({
                                        "success": True,
                                        "fileName": asset["name"],
                                        "downloadUrl": f"/api/git/download-bundle?filename={bundle_path.name}"
                                    }, ensure_ascii=False).encode("utf-8")
                                    self.send_content(body, "application/json; charset=utf-8")
                                    return

                    body = json.dumps({"error": "No release found for this commit"}, ensure_ascii=False).encode("utf-8")
                    self.send_content(body, "application/json; charset=utf-8", HTTPStatus.NOT_FOUND)

                except urllib.error.HTTPError as e:
                    if e.code == 401:
                        body = json.dumps({"error": "Invalid GitHub token"}, ensure_ascii=False).encode("utf-8")
                    elif e.code == 404:
                        body = json.dumps({"error": "Repository not found or no releases"}, ensure_ascii=False).encode("utf-8")
                    else:
                        body = json.dumps({"error": f"GitHub API error: {e.code}"}, ensure_ascii=False).encode("utf-8")
                    self.send_content(body, "application/json; charset=utf-8", e.code)
                except Exception as e:
                    body = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
                    self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)

            except subprocess.TimeoutExpired:
                body = json.dumps({"error": "Git operation timed out"}, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", HTTPStatus.REQUEST_TIMEOUT)
            except Exception as e:
                print(f"[Web Dashboard] GitHub download error: {e}")
                body = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/git/install":
            print(f"[Web Dashboard] API /api/git/install - Installing git")
            success, message = install_git()
            body = json.dumps({"success": success, "message": message}, ensure_ascii=False).encode("utf-8")
            status = HTTPStatus.OK if success else HTTPStatus.INTERNAL_SERVER_ERROR
            self.send_content(body, "application/json; charset=utf-8", status)
            return

        if self.path == "/api/register-log":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                action = payload.get("action")
                print(f"[Web Dashboard] API /api/register-log - Action: {action}")
                if action == "start":
                    result = start_register_log(
                        str(payload.get("language", "uk")),
                        payload.get("translations"),
                    )
                elif action == "stop":
                    result = stop_register_log()
                elif action == "mark":
                    with state_lock:
                        cycle_id = int(state["cycle_id"])
                    result = record_register_log_note(
                        str(payload.get("note", "")), cycle_id
                    )
                elif action == "lcd_key":
                    with state_lock:
                        cycle_id = int(state["cycle_id"])
                    result = record_demo_lcd_key(
                        str(payload.get("key", "")),
                        str(payload.get("page", "")),
                        str(payload.get("demo_case", "")),
                        cycle_id,
                    )
                else:
                    raise ValueError("action має бути start, stop, mark або lcd_key")
                print(f"[Web Dashboard] API /api/register-log - Result: {result.get('error') or 'success'}")
                status = (
                    HTTPStatus.INTERNAL_SERVER_ERROR
                    if result.get("error")
                    else HTTPStatus.OK
                )
                body = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", status)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                print(f"[Web Dashboard] API /api/register-log - Error: {error}")
                body = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_content(
                    body, "application/json; charset=utf-8", HTTPStatus.BAD_REQUEST
                )
            return

        if self.path == "/api/connection-mode":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                action = payload.get("action")
                print(f"[Web Dashboard] API /api/connection-mode - Action: {action}, Mode: {payload.get('mode')}")
                if action == "set":
                    result = set_connection_mode(str(payload.get("mode", "rtu")))
                elif action == "get":
                    result = get_connection_mode()
                else:
                    raise ValueError("action має бути set або get")
                print(f"[Web Dashboard] API /api/connection-mode - Result: {result}")
                status = (
                    HTTPStatus.BAD_REQUEST if result.get("error") else HTTPStatus.OK
                )
                body = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", status)
            except (ValueError, OSError, json.JSONDecodeError) as error:
                print(f"[Web Dashboard] API /api/connection-mode - Error: {error}")
                body = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_content(
                    body, "application/json; charset=utf-8", HTTPStatus.BAD_REQUEST
                )
            return

        if self.path != "/api/settings":
            self.send_content(
                '{"error":"не знайдено"}'.encode("utf-8"),
                "application/json",
                HTTPStatus.NOT_FOUND,
            )
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            print(f"[Web Dashboard] API /api/settings - Payload: {payload}")
            with state_lock:
                if "poll_rate_index" in payload:
                    index = int(payload["poll_rate_index"])
                    if not 0 <= index < len(POLL_RATES):
                        raise ValueError("неправильний інтервал опитування")
                    state["poll_rate_index"] = index
                if "read_mode" in payload:
                    mode = str(payload["read_mode"])
                    if mode not in {"fast", "compatible"}:
                        raise ValueError("неправильний режим читання")
                    state["read_mode"] = mode
                if "paused" in payload:
                    paused = payload["paused"]
                    if not isinstance(paused, bool):
                        raise ValueError("paused має бути true або false")
                    state["paused"] = paused
            print(f"[Web Dashboard] API /api/settings - Applied changes")
            poll_wake_event.set()
            self.send_content(b'{"ok":true}', "application/json")
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            print(f"[Web Dashboard] API /api/settings - Error: {error}")
            body = json.dumps({"error": str(error)}).encode("utf-8")
            self.send_content(body, "application/json", HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_web_dashboard() -> None:
    host = os.environ.get("INVERTER_WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("INVERTER_WEB_PORT", "8080"))
    initialise_statistics()
    maintain_register_log_storage(force=True)
    register_log_storage_stop_event.clear()
    storage_worker = threading.Thread(
        target=register_log_storage_worker,
        name="register-log-storage",
        daemon=True,
    )
    storage_worker.start()
    worker = threading.Thread(target=poll_worker, name="inverter-poller", daemon=True)
    worker.start()
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    safe_console_print(f"Solar Inverter Web: http://localhost:{port}")
    safe_console_print(
        f"Прослуховування {host}:{port} — натисніть Ctrl+C для зупинки"
    )
    if inverter_service.stats_error:
        safe_console_print(f"Лічильник відвідувачів вимкнено: {inverter_service.stats_error}")
    else:
        safe_console_print(
            f"Лічильник: {inverter_service.site_visit_total} відвідувачів · {STATS_DB_PATH}"
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        register_log_storage_stop_event.set()
        stop_register_log()
        flush_solar_energy()
        with state_lock:
            state["stop"] = True
        poll_wake_event.set()
        server.server_close()
