# Orange Pi deployment and update guide

This guide installs the dashboard as `solar-inverter-dashboard.service`, reads the inverter from `/dev/ttyUSB0`, and exposes the local web server through a Tailscale machine named `tailsweb`.

The recommended setup binds the Python server only to `127.0.0.1:8080`. Tailscale terminates HTTPS and proxies requests to that loopback address.

## Single-file update (recommended for a direct SSH connection)

The repository can build one self-installing Python archive containing only the web dashboard runtime and systemd unit. On the development PC, rebuild it after every application change:

```powershell
py -3 deploy/build_update_bundle.py
py -3 deploy/solar-dashboard-update.pyz --check
scp deploy/solar-dashboard-update.pyz "orangepi@ORANGE_PI_IP:~/"
```

Then connect to the Orange Pi and run the one copied file:

```bash
ssh orangepi@ORANGE_PI_IP
sudo python3 ~/solar-dashboard-update.pyz
```

The updater validates its embedded Python files before installation, creates the restricted service account when necessary, installs missing `git`, `mbpoll`, or timezone data through `apt-get`, updates only the required application files, installs the systemd unit, restarts the service, and checks `http://127.0.0.1:8080/api/state`.

It does not replace the statistics database, register logs, Tailscale configuration, optional integration, Android project, or documentation. To inspect a copied archive without changing the Orange Pi, run:

```bash
python3 ~/solar-dashboard-update.pyz --check
```

## 1. Publish the new version

On the development computer, commit only application and deployment source files. Do not commit runtime databases, register logs, or `__pycache__` files.

```bash
git status
git add solar_invertor_web.py favicon.png deploy/solar-inverter-dashboard.service deploy/ORANGE_PI_DEPLOYMENT.md solar_inverter/__init__.py solar_inverter/components/*.py solar_inverter/services/*.py
git commit -m "Update solar inverter dashboard"
git push origin main
```

The Orange Pi cannot receive local, uncommitted changes. Confirm the new commit is visible in the configured GitHub repository before continuing.

## 2. Install Orange Pi packages

Connect to the Orange Pi over SSH and install the runtime tools:

```bash
sudo apt update
sudo apt install -y python3 git mbpoll curl ca-certificates tzdata
python3 --version
mbpoll -V
```

The application uses only the Python standard library; it does not require `pip` packages.

## 3. Install the application

Use the single-file updater from the first section. It creates the service account, application directory, persistent-data directory, and systemd unit with the paths required by the installed release. This avoids manual path changes and preserves existing runtime data.

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

The updater validates the source, installs the supplied unit, and starts it. Check the resulting service:

```bash
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

## 9. Check or install a later GitHub version

When the dashboard was installed from a Git checkout, use the copied updater archive
to fetch GitHub and compare the installed dashboard build with the latest commit:

```bash
sudo python3 ~/solar-dashboard-update.pyz --github-status
```

This only fetches Git metadata and prints the local dashboard asset version, local
commit, latest GitHub commit, and whether updates are available. It does not restart
or modify the dashboard.

To install available commits, use the explicit fast-forward updater command:

```bash
sudo python3 ~/solar-dashboard-update.pyz --github-update
```

The command refuses to overwrite local commits or a diverged checkout. It validates
the updated Python entry point, restarts the service, and confirms the running
dashboard asset version through the local API. GitHub CLI is not required on the
Orange Pi; the updater uses the `git` package installed during setup.

### Manual update alternative

First commit and push the new version from the development computer as described in step 1. Then run this on the Orange Pi:

```bash
sudo python3 ~/solar-dashboard-update.pyz
sudo systemctl status solar-inverter-dashboard.service --no-pager
curl -fsS http://127.0.0.1:8080/api/state >/dev/null && echo "Updated dashboard OK"
```

Tailscale Serve or Funnel does not need to be reconfigured for normal application updates because it continues proxying the same local port.

Do not use `git clean` in the application directory: runtime register logs must be preserved.

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
