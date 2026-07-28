# Orange Pi deployment and update guide

This guide installs the dashboard as `solar-inverter-dashboard.service`, reads the inverter from `/dev/ttyUSB0`, and exposes the local web server through a Tailscale machine named `tailsweb`.

The recommended setup binds the Python server only to `127.0.0.1:8080`. Tailscale terminates HTTPS and proxies requests to that loopback address.

## 1. Publish the new version

On the development computer, commit only application and deployment source files. Do not commit runtime databases, register logs, or `__pycache__` files.

```bash
git status
git add solar_invertor_web.py favicon.png deploy/solar-inverter-dashboard.service deploy/ORANGE_PI_DEPLOYMENT.md solar_inverter/__init__.py solar_inverter/components/*.py solar_inverter/services/*.py
git commit -m "Update solar inverter dashboard"
git push origin main
```

The Orange Pi cannot receive local, uncommitted changes. Confirm the new commit is visible at `https://github.com/santaes/solar_assistant` before continuing.

## 2. Install Orange Pi packages

Connect to the Orange Pi over SSH and install the runtime tools:

```bash
sudo apt update
sudo apt install -y python3 git mbpoll curl ca-certificates tzdata
python3 --version
mbpoll -V
```

The application uses only the Python standard library; it does not require `pip` packages.

## 3. Create the service account and clone the app

```bash
sudo useradd --system --user-group --home-dir /opt/solar_assistant --shell /usr/sbin/nologin solar-dashboard
sudo usermod -aG dialout solar-dashboard
sudo install -d -o solar-dashboard -g solar-dashboard /opt/solar_assistant
sudo -u solar-dashboard git clone https://github.com/santaes/solar_assistant.git /opt/solar_assistant
sudo install -d -o solar-dashboard -g solar-dashboard -m 0750 /var/lib/solar-inverter-dashboard
```

If `solar-dashboard` or `/opt/solar_assistant` already exists, do not recreate it. Verify ownership instead:

```bash
sudo chown -R solar-dashboard:solar-dashboard /opt/solar_assistant
sudo usermod -aG dialout solar-dashboard
```

For a private GitHub repository, configure a read-only deploy key for the `solar-dashboard` account before cloning.

## 4. Verify the USB Modbus adapter

The current application is configured for `/dev/ttyUSB0`, Modbus slave `1`, and `9600` baud.

```bash
ls -l /dev/ttyUSB0
id solar-dashboard
sudo -u solar-dashboard test -r /dev/ttyUSB0
sudo -u solar-dashboard test -w /dev/ttyUSB0
sudo -u solar-dashboard mbpoll -m rtu -b 9600 -P none -t 4 -a 1 -r 89 -c 1 -1 -q /dev/ttyUSB0
```

Both `test` commands must succeed. If they fail, unplug/reconnect the adapter and check:

```bash
dmesg --follow
ls -l /dev/ttyUSB*
```

If the adapter appears as `/dev/ttyUSB1`, the current source must be changed or a stable udev symlink must be created before starting the service.

## 5. Install and start the systemd service

Validate the source, install the supplied unit, and start it:

```bash
sudo -u solar-dashboard python3 -m py_compile /opt/solar_assistant/solar_invertor_web.py
sudo install -m 0644 /opt/solar_assistant/deploy/solar-inverter-dashboard.service /etc/systemd/system/solar-inverter-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now solar-inverter-dashboard.service
sudo systemctl status solar-inverter-dashboard.service --no-pager
```

Check the local API:

```bash
curl -fsS http://127.0.0.1:8080/api/state >/dev/null && echo "Local dashboard OK"
```

Follow logs if it does not start:

```bash
sudo journalctl -u solar-inverter-dashboard.service -f
```

## 6. Install Tailscale and name the machine `tailsweb`

Install Tailscale on the Orange Pi, authenticate it to the correct tailnet, and set its machine name:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
sudo tailscale set --hostname=tailsweb
tailscale status
tailscale ip -4
```

Open the authentication URL printed by `tailscale up`. In the Tailscale admin console, confirm that the machine is named exactly `tailsweb`. If another active or expired machine already has that name, Tailscale may assign `tailsweb-1`; rename or remove the old entry first if the stable `tailsweb` URL is required.

## 7. Expose the dashboard

Choose one exposure mode.

### Private: tailnet members only (recommended)

```bash
sudo tailscale serve --bg http://127.0.0.1:8080
sudo tailscale serve status
```

Open the HTTPS URL printed by `tailscale serve status`, normally:

```text
https://tailsweb.<your-tailnet>.ts.net
```

### Public internet: Tailscale Funnel

The dashboard currently has no application login. Funnel exposes its controls and API to anyone who knows the URL. Use this only when public access is intentional.

```bash
sudo tailscale funnel --bg http://127.0.0.1:8080
sudo tailscale funnel status
```

Open the HTTPS URL printed by `tailscale funnel status`. Public DNS may need several minutes to become available after Funnel is enabled for the first time.

Do not run `tailscale web` for this dashboard. That command serves Tailscale's administrative UI; `tailsweb` here is only the Orange Pi's machine name.

## 8. Verify the complete deployment

```bash
systemctl is-active solar-inverter-dashboard.service
curl -fsS http://127.0.0.1:8080/api/state >/dev/null && echo "Local API OK"
sudo tailscale serve status
sudo tailscale funnel status
```

Then test the selected `https://tailsweb.<your-tailnet>.ts.net` URL from another device. Confirm that:

- the dashboard loads;
- `/api/state` returns JSON;
- the header shows current update cycles;
- Modbus readings do not report `mbpoll not found`, `Permission denied`, or a missing `/dev/ttyUSB0`.

## 9. Install a later version

First commit and push the new version from the development computer as described in step 1. Then run this on the Orange Pi:

```bash
sudo systemctl stop solar-inverter-dashboard.service
sudo cp -a /var/lib/solar-inverter-dashboard/stats.sqlite3 /var/lib/solar-inverter-dashboard/stats.sqlite3.backup 2>/dev/null || true
sudo -u solar-dashboard git -C /opt/solar_assistant fetch origin
sudo -u solar-dashboard git -C /opt/solar_assistant pull --ff-only origin main
sudo -u solar-dashboard python3 -m py_compile /opt/solar_assistant/solar_invertor_web.py
sudo install -m 0644 /opt/solar_assistant/deploy/solar-inverter-dashboard.service /etc/systemd/system/solar-inverter-dashboard.service
sudo systemctl daemon-reload
sudo systemctl start solar-inverter-dashboard.service
sudo systemctl status solar-inverter-dashboard.service --no-pager
curl -fsS http://127.0.0.1:8080/api/state >/dev/null && echo "Updated dashboard OK"
```

Tailscale Serve or Funnel does not need to be reconfigured for normal application updates because it continues proxying the same local port.

Do not use `git clean` in the deployment directory: runtime register logs are stored under `/opt/solar_assistant/register_logs`.

## 10. Troubleshooting

### Service fails immediately

```bash
sudo systemctl status solar-inverter-dashboard.service --no-pager
sudo journalctl -u solar-inverter-dashboard.service -n 100 --no-pager
```

### `mbpoll` is missing

```bash
sudo apt install -y mbpoll
command -v mbpoll
```

### `/dev/ttyUSB0` permission denied

```bash
sudo usermod -aG dialout solar-dashboard
sudo systemctl restart solar-inverter-dashboard.service
id solar-dashboard
```

### Local API works but the HTTPS URL fails

```bash
tailscale status
sudo tailscale serve status
sudo tailscale funnel status
curl -fsS http://127.0.0.1:8080/api/state >/dev/null
```

Re-run only the exposure command for the mode being used. Do not expose port `8080` through the router or bind the Python service to `0.0.0.0`; Tailscale should be the only external entry point.

## References

- [Install Tailscale on Linux](https://tailscale.com/docs/install/linux)
- [Tailscale Serve CLI](https://tailscale.com/docs/reference/tailscale-cli/serve)
- [Tailscale Funnel CLI](https://tailscale.com/docs/reference/tailscale-cli/funnel)
- [Tailscale machine names](https://tailscale.com/docs/concepts/machine-names)
- [Debian `mbpoll` package](https://packages.debian.org/bookworm/mbpoll)
