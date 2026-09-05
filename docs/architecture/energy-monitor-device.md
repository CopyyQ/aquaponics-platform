# Energy Monitor Device

## Domain model

An Energy Monitor is an ordinary runtime `Device` owned by a `Project`. It is classified only by `Device.device_template_id -> DeviceTemplate.device_kind == ENERGY_MONITOR`. Its measurements use the existing `SensorModel -> Sensor -> TelemetryReading -> TelemetryAggregate` chain. There are no energy-specific runtime or telemetry tables.

## Template and catalog

The built-in template is `ENERGY_MONITOR_12V`, has a nominal output voltage of 12 V and no Actuator mappings. It requires exactly one mapping for each model, in this order:

| SensorModel | Sensor code | Unit | Semantics |
|---|---|---|---|
| `OUTPUT_VOLTAGE_V` | `OUTPUT-VOLTAGE` | V | GAUGE |
| `INPUT_VOLTAGE_V` | `INPUT-VOLTAGE` | V | GAUGE |
| `LOAD_CURRENT_A` | `LOAD-CURRENT` | A | GAUGE |
| `INPUT_CURRENT_A` | `INPUT-CURRENT` | A | GAUGE |
| `POWER_W` | `POWER` | W | GAUGE |
| `ENERGY_TOTAL_WH` | `ENERGY` | Wh | COUNTER |

Template activation and Device creation validate completeness, uniqueness, unit, NUMBER value type and measurement semantics. Template materialization is one transaction and creates no Actuator.

## MQTT payload

The topic remains `aquaponics/{device_code}/telemetry`. Firmware sends `sensor_code`, numeric `value` and ISO-8601 `recorded_at`; it does not send Project, Device, Sensor or SensorModel database IDs. The Backend resolves Project ownership through the topic's Device code and rejects disabled runtime context.

```json
{
  "sent_at": "2026-08-05T04:30:00Z",
  "readings": [
    {"sensor_code": "OUTPUT-VOLTAGE", "value": 11.92, "recorded_at": "2026-08-05T04:30:00Z"},
    {"sensor_code": "INPUT-VOLTAGE", "value": 24.1, "recorded_at": "2026-08-05T04:30:00Z"},
    {"sensor_code": "LOAD-CURRENT", "value": 3.21, "recorded_at": "2026-08-05T04:30:00Z"},
    {"sensor_code": "INPUT-CURRENT", "value": 1.73, "recorded_at": "2026-08-05T04:30:00Z"},
    {"sensor_code": "POWER", "value": 38.4, "recorded_at": "2026-08-05T04:30:00Z"},
    {"sensor_code": "ENERGY", "value": 12842.7, "recorded_at": "2026-08-05T04:30:00Z"}
  ]
}
```

## Configuration JSON

The Project-scoped connection-config endpoint preserves existing schema keys and adds Project/Device IDs, Device kind/template metadata, nominal voltage, Sensor semantics/required flags, explicit broker/topic aliases and an `energy_monitoring` contract. It contains no password, JWT, certificate or secret. `1m` is explicitly mapped to `ONE_MONTH`.

## Dedicated dashboard and APIs

An Energy Monitor renders the dedicated Device dashboard at `/admin/projects/{projectId}/devices/{deviceId}`, selected solely from `DeviceTemplate.device_kind`. It loads a project-scoped `energy-overview` read model and an `energy-power-series` read model. The overview returns all six nullable measurements, counter-derived 1h/6h/24h/month consumption, separate `recorded_at`/`received_at`, freshness, engineering quality, data-health counters and grouped root issues. The chart is the only energy chart in v1 and displays valid `POWER_W` averages for `1h`, `6h`, `24h` and `1m` (one month). Missing buckets remain gaps, never zero.

Project Overview may only show a compact link to each Energy Device. Project Monitoring has no Energy tab; legacy `tab=energy` URLs are normalized to the standard monitoring page.

Disabled Devices stay visible in Energy inventory with historical values; soft-deleted Devices are excluded. Activation returns connectivity to `WAITING_CONNECTION` rather than simulating ONLINE.

## Known unknowns and extension points

The electrical system may be AC or DC and measurement points are not confirmed, so power must not be derived from `V × I`. `ENERGY_TOTAL_WH` remains the sole raw cumulative counter. Period deltas sum monotonic segments and treat a decrease as reset; billing, tariff and carbon calculations remain out of scope. Future Device kinds extend the template discriminator and their own validators without duplicating runtime tables.
