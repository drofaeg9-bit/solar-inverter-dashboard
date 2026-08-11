# Orange Pi deployment

The production service runs as the restricted `solar-dashboard` account, reads `/dev/ttyUSB0` through the `dialout` group, binds to `127.0.0.1:8080`, and stores persistent statistics in `/var/lib/solar-inverter-dashboard/`.

## Update checklist

```bash
sudo python3 ~/solar-dashboard-update.pyz
curl -fsS http://127.0.0.1:8080/api/state >/dev/null
```

Tailscale Serve continues proxying the same loopback port after normal application updates, so it does not need to be reconfigured.

For first installation, USB checks, Tailscale Serve/Funnel setup, backup steps, and troubleshooting, use the repository's complete `deploy/ORANGE_PI_DEPLOYMENT.md` guide.
