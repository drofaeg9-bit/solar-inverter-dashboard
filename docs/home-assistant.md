# Home Assistant integration

The custom integration lives under `custom_components/solar_assistant/` and declares the domain `solar_assistant`.

## Connection modes

- Local or cloud SolarAssistant access uses `SolarAssistantCoordinator`, REST discovery, and a reconnecting WebSocket stream.
- Direct Modbus TCP uses `ModbusCoordinator` and a fixed register mapping.

The selected coordinator is stored under `hass.data[DOMAIN][entry_id]`. Home Assistant then forwards setup to these platforms:

- `binary_sensor`
- `number`
- `select`
- `sensor`
- `switch`

## WebSocket coordinator

`SolarAssistantCoordinator` preloads metric definitions through REST, starts one WebSocket per configuration entry, publishes changes through Home Assistant dispatcher signals, and reconnects with exponential backoff. It can recover a changed device IP through mDNS and refresh cloud authorization when required.

## Direct Modbus coordinator

`ModbusCoordinator` connects with `pymodbus`, reads holding registers, converts known values to engineering units, and exposes the result through Home Assistant's `DataUpdateCoordinator` interface.

## Entity lifecycle

Metric entities share `SolarAssistantMetricEntity`. Entity platforms subscribe to new-metric and update signals. When enabled-topic options change, excluded read-only sensors are removed before the configuration entry reloads; settings entities and the connection binary sensor remain independently managed.
