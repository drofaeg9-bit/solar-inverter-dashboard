# Project overview

The repository contains three user-facing applications built around solar-inverter data:

| Area | Location | Purpose |
| --- | --- | --- |
| Web dashboard | `solar_inverter/` | Polls the inverter, normalizes registers, serves the dashboard and JSON API |
| Home Assistant | `custom_components/solar_assistant/` | Creates Home Assistant entities from WebSocket, REST, or Modbus data |
| Android client | `android_app/` | Displays the existing dashboard in an Android WebView |

## Runtime requirements

- Python 3 and the standard library for the standalone dashboard.
- `mbpoll` for Modbus RTU reads from `/dev/ttyUSB0`.
- Read/write access to the serial adapter.
- SQLite storage for page-view counts and estimated solar-energy totals.
- Node.js only when regenerating this documentation.

## Data lifecycle

1. The polling worker invokes `mbpoll` for configured register blocks.
2. Raw 16-bit values are cached and normalized into engineering units.
3. The HTTP handler exposes the state at `GET /api/state`.
4. The browser polls that endpoint and updates dashboard cards, charts, LCD view, and energy-flow animation.
5. Solar production and optional register-change records are persisted independently.

The browser demo mode generates client-side samples. Demo generator values are intentionally not presented as physical Modbus registers.
