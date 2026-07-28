# Dashboard API

The standalone service exposes a small same-origin HTTP API. It currently has no application-level authentication; production access should be restricted with Tailscale Serve or another trusted reverse proxy.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Dashboard HTML with initial state embedded in the page |
| `GET` | `/api/state` | Latest normalized inverter state |
| `GET` | `/api/register-log/download` | Active or latest register log as CSV |
| `POST` | `/api/settings` | Change poll interval, read mode, or pause state |
| `POST` | `/api/register-log` | Start, stop, annotate, or record an LCD demo event |

All dynamic responses use `Cache-Control: no-store`.

## Settings example

```javascript
const response = await fetch('/api/settings', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    poll_rate_index: 2,
    read_mode: 'fast',
    paused: false
  })
});
```

`poll_rate_index` must refer to an entry in the `poll_rates` array returned by `/api/state`. The read mode is either `fast` or `compatible`.

## Register-log examples

```javascript
await fetch('/api/register-log', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({action: 'start', language: 'en'})
});

await fetch('/api/register-log', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({action: 'mark', note: 'Changed inverter setting'})
});
```

See the Compodoc Interfaces and Classes sections for the typed response and request contracts.
