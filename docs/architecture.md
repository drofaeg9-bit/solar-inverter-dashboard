# Architecture

## Standalone dashboard

```text
/dev/ttyUSB0
    |
  mbpoll
    |
inverter_service.py ---- SQLite statistics
    |                 \\-- CSV register logs
    |
web_dashboard.py :8080
    |
dashboard_template.py (HTML/CSS/JavaScript)
    |
Browser or Android WebView
```

`solar_invertor_web.py` is a compatibility entry point. It delegates startup to `run_web_dashboard()`.

### Service layer

`solar_inverter/services/inverter_service.py` owns:

- device configuration and register metadata;
- fast block reads and compatible one-register reads;
- signed 16-bit conversion and engineering-unit normalization;
- synchronized shared state and the background poll worker;
- SQLite statistics and solar-energy integration;
- CSV register-change logging and storage cleanup.

### HTTP layer

`solar_inverter/components/web_dashboard.py` uses Python's `ThreadingHTTPServer`. It serializes a snapshot under the state lock and serves static dashboard HTML, JSON state, settings changes, and register-log operations.

### Browser layer

`solar_inverter/components/dashboard_template.py` is a Python raw string containing the complete dashboard document. The browser owns localization, demo samples, charts, energy-flow rendering, responsive layout, and regular `/api/state` refreshes.

## Concurrency

The HTTP server handles requests on separate threads. Shared poll state, statistics, and register-log state have dedicated locks. The poll worker can be interrupted when settings change through `poll_wake_event`, allowing pause and interval changes to take effect without waiting for the previous interval.

## Persistence

- `INVERTER_STATS_DB` selects the SQLite database path.
- `register_logs/` stores timestamped CSV files.
- Low-disk cleanup removes the oldest completed logs but preserves the active log.
- Production uses `/var/lib/solar-inverter-dashboard/stats.sqlite3` through the systemd unit.
