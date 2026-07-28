# Orange Pi deployment

The production service runs as the restricted `solar-dashboard` account, reads `/dev/ttyUSB0` through the `dialout` group, binds to `127.0.0.1:8080`, and stores persistent statistics in `/var/lib/solar-inverter-dashboard/`.

## Update checklist

```bash
sudo systemctl stop solar-inverter-dashboard.service
sudo -u solar-dashboard git -C /opt/solar_assistant pull --ff-only origin main
sudo -u solar-dashboard python3 -m py_compile /opt/solar_assistant/solar_invertor_web.py
sudo install -m 0644 /opt/solar_assistant/deploy/solar-inverter-dashboard.service /etc/systemd/system/solar-inverter-dashboard.service
sudo systemctl daemon-reload
sudo systemctl start solar-inverter-dashboard.service
curl -fsS http://127.0.0.1:8080/api/state >/dev/null
```

Tailscale Serve continues proxying the same loopback port after normal application updates, so it does not need to be reconfigured.

For first installation, USB checks, Tailscale Serve/Funnel setup, backup steps, and troubleshooting, use the repository's complete `deploy/ORANGE_PI_DEPLOYMENT.md` guide.
