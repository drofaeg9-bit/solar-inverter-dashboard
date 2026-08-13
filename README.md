# Solar Inverter Dashboard

Solar Inverter Dashboard reads an inverter over Modbus RTU, serves a responsive browser dashboard, records solar-energy totals and register-change logs, and can expose the service through Tailscale. The repository also contains an optional automation-platform integration and an Android WebView client.

## Main applications

- `solar_invertor_web.py` starts the Python web dashboard.
- `solar_inverter/services/inverter_service.py` polls and normalizes inverter registers.
- `solar_inverter/components/web_dashboard.py` serves the HTML application and JSON API.
- `solar_inverter/components/dashboard_template.py` contains the browser UI.
- `custom_components/` contains the optional automation-platform integration.
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

By default the dashboard listens on port `8080`. Production deployment instructions are included in the generated Project Guide and in `deploy/ORANGE_PI_DEPLOYMENT.md`. For a new Orange Pi 3 LTS running the exact `lts_2.2.2_debian_buster_desktop_linux5.10.75.7z` image, begin with `deploy/ORANGE_PI_3_LTS_BUSTER_FIRST_INSTALL.md`.

## Connect to the real inverter

The dashboard deliberately does not generate measurement values: it only shows
what Modbus returns. Configure the connection before starting it. For a Modbus
TCP gateway, set `INVERTER_CONNECTION_MODE=tcp`, `INVERTER_TCP_HOST` and,
when needed, `INVERTER_TCP_PORT` and `INVERTER_SLAVE_ID`. For a USB/RS-232 or USB/RS-485
adapter, set `INVERTER_SERIAL_DEVICE` (for example `COM3` on Windows or
`/dev/ttyUSB0` on Linux), `INVERTER_BAUD_RATE` and `INVERTER_SLAVE_ID`.

Example in PowerShell:

```powershell
$env:INVERTER_CONNECTION_MODE = 'tcp'
$env:INVERTER_TCP_HOST = '192.168.1.50'
$env:INVERTER_TCP_PORT = '502'
python solar_invertor_web.py
```

## Build the single-file Orange Pi updater

```bash
python3 deploy/build_update_bundle.py
python3 deploy/solar-dashboard-update.pyz --check
```

Copy only `deploy/solar-dashboard-update.pyz` to the Orange Pi and run it with `sudo python3`. The archive contains every deployable project source file from this workspace—including documentation, tests, Android sources, configuration, scripts, and assets—and its manifest checksum-verifies every file before installation. It excludes only Git metadata, virtual environments, `node_modules`, caches/build outputs, the archive itself, and live databases/logs. The updater restarts the systemd service and verifies the local API without overwriting persistent statistics or register logs.
