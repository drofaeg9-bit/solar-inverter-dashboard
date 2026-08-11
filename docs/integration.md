# Optional platform integration

The custom integration is located under `custom_components/`.

## Connection modes

- Local or cloud access uses REST discovery and a reconnecting WebSocket stream.
- Direct Modbus TCP uses a fixed register mapping.

The selected coordinator is stored for each configuration entry. The platform then forwards setup to these entity types:

- `binary_sensor`
- `number`
- `select`
- `sensor`
- `switch`

## WebSocket coordinator

The cloud coordinator preloads metric definitions through REST, starts one WebSocket per configuration entry, publishes changes through dispatcher signals, and reconnects with exponential backoff. It can recover a changed device IP through mDNS and refresh cloud authorization when required.

## Direct Modbus coordinator

The Modbus coordinator connects with `pymodbus`, reads holding registers, converts known values to engineering units, and exposes the result through the platform update-coordinator interface.

## Entity lifecycle

Metric entities share a common base class. Entity platforms subscribe to new-metric and update signals. When enabled-topic options change, excluded read-only sensors are removed before the configuration entry reloads; settings entities and the connection binary sensor remain independently managed.
