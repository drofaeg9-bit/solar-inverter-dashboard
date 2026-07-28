# Solar Inverter Dashboard

Solar Inverter Dashboard reads an inverter over Modbus RTU, serves a responsive browser dashboard, records solar-energy totals and register-change logs, and can expose the service through Tailscale. The repository also contains a Home Assistant custom integration and an Android WebView client.

## Main applications

- `solar_invertor_web.py` starts the Python web dashboard.
- `solar_inverter/services/inverter_service.py` polls and normalizes inverter registers.
- `solar_inverter/components/web_dashboard.py` serves the HTML application and JSON API.
- `solar_inverter/components/dashboard_template.py` contains the browser UI.
- `custom_components/solar_assistant/` contains the Home Assistant integration.
- `android_app/` contains the Android wrapper application.

## Generate documentation

Node.js 20, 22, or 24 is recommended.

```bash
npm install
npm run docs:generate
```

Open `documentation/index.html`, or run a local documentation server:

```bash
npm run docs:serve
```

The server listens at `http://127.0.0.1:8081`.

## Run the dashboard

The runtime requires Python 3, `mbpoll`, and access to `/dev/ttyUSB0`.

```bash
python3 solar_invertor_web.py
```

By default the dashboard listens on port `8080`. Production deployment instructions are included in the generated Project Guide and in `deploy/ORANGE_PI_DEPLOYMENT.md`.
