# Telegram workbook mapping

Source: `Yêu cầu thông báo Telegram Aquaponics.xlsx`, Sheet1, inspected in full
on 2026-09-08. The workbook note says yellow rows are not currently required.
Yellow fill was verified from the XLSX cell styles, not inferred from text.

Runtime numeric Sensor thresholds are always materialized in and read from
`threshold_alert_configs`. Values shown below from the workbook are seed/default
guidance only; they are never read from the message catalog at runtime.

## Row mapping

| Excel row / STT | Classification | condition_key | Evaluator and semantic mapping | Threshold source | Risk | Message/content |
|---|---|---|---|---|---|---|
| 4 / 1 DO bể cá | Disabled (yellow; Sensor unavailable) | `SENSOR_DO_LOW` | Future Sensor semantic code `DO` | Future canonical config | HIGH/VERY_HIGH by direction/config | Source says unavailable; no active send. |
| 5 / 2 Máy sủi Oxy, 12 V + 0 A | Active actuator composite | `ACTUATOR_ON_NO_LOAD` | Actuator ON + voltage near nominal + current below minimum | ActuatorModel electrical capability | VERY_HIGH | Oxygen delivery may stop; verify plug, wiring and aerator. |
| 6 / 3 Máy sủi Oxy, 0 V + 0 A | Active actuator composite | `ACTUATOR_NO_POWER` | Actuator ON + voltage near zero + current near zero; precedence over ON_NO_LOAD | ActuatorModel electrical capability | EXTREME | Possible power/relay/driver/wiring loss. |
| 7 / 4 Bơm bể cá, 12 V + 0 A | Active actuator composite | `ACTUATOR_ON_NO_LOAD` | Same generic rule, semantic actuator model identifies pump | ActuatorModel electrical capability | VERY_HIGH | Circulation may have stopped; inspect connector, blockage and pump. |
| 8 / 5 Bơm bể cá, 0 V + 0 A | Active actuator composite | `ACTUATOR_NO_POWER` | Same precedence rule | ActuatorModel electrical capability | EXTREME | Possible source/switching/wiring failure. |
| 9 / 6 Bơm tưới giàn, 12 V + 0 A | Active actuator composite | `ACTUATOR_ON_NO_LOAD` | Same generic rule | ActuatorModel electrical capability | VERY_HIGH | Grow-bed water circulation may stop. |
| 10 / 7 Bơm tưới giàn | Active but ambiguous source row | `ACTUATOR_NO_POWER` | Interpret message's 0 V + 0 A because it is distinct from row 9 | ActuatorModel electrical capability | EXTREME | Possible source/switching/wiring failure. |
| 11 / 8 Mức nước bể lọc vi sinh thấp | Active Sensor threshold | `SENSOR_WATER_LEVEL_LOW` | Semantic Sensor model `WATER_LEVEL`; location/resource context in snapshot | `threshold_alert_configs.lower_threshold` | LOW default unless configured | Protect biofilter and circulation; check fish-tank pump and connecting pipes. |
| 12 / 9 Mức nước bể cá thấp | Active Sensor threshold | `SENSOR_WATER_LEVEL_LOW` | Same semantic model, resource/location snapshot distinguishes it | `threshold_alert_configs.lower_threshold` | LOW default unless configured | Check inlet valve, pumps, return path and leakage. |
| 13 / 10 Đèn, 12 V + 0 A | Active actuator composite | `ACTUATOR_ON_NO_LOAD` | Generic electrical rule + actuator model | ActuatorModel electrical capability | HIGH | Lighting may not operate; inspect connector and lamp. |
| 14 / 11 Đèn, 0 V + 0 A | Active actuator composite | `ACTUATOR_NO_POWER` | Generic electrical rule + actuator model | ActuatorModel electrical capability | VERY_HIGH | Possible source/switching/wiring failure. |
| 15 / 12 pH cao | Active Sensor threshold | `SENSOR_PH_HIGH` | Sensor model code `PH`, ABOVE direction | `threshold_alert_configs.upper_threshold` | HIGH default unless configured | Verify contamination and water conditions; adjust gradually and remeasure. |
| 16 / 13 pH thấp | Active Sensor threshold | `SENSOR_PH_LOW` | Sensor model code `PH`, BELOW direction | `threshold_alert_configs.lower_threshold` | LOW default unless configured | Verify contamination/source water; correct gradually and remeasure. |
| 17 / 14 Nhiệt độ nước cao | Active Sensor threshold | `SENSOR_WATER_TEMPERATURE_HIGH` | Sensor model `WATER_TEMPERATURE`/`TEMP`, ABOVE | `threshold_alert_configs.upper_threshold` | HIGH default unless configured | Shade the tank, verify circulation/aeration, cool gradually. |
| 18 / 15 Flow giảm | Disabled (yellow; Sensor unavailable) | `SENSOR_FLOW_LOW` | Future flow semantic | Future canonical config | HIGH | Source says unavailable; no active send. |
| 19 / 16 NH3/NH4 | Disabled (yellow; Sensor unavailable) | `SENSOR_AMMONIA_HIGH` | Future semantic | Future canonical config | VERY_HIGH | Source says unavailable; no active send. |
| 20 / 17 NO2 | Disabled (yellow; Sensor unavailable) | `SENSOR_NITRITE_HIGH` | Future semantic | Future canonical config | VERY_HIGH/EXTREME | Source says unavailable; no active send. |
| 21 / 18 TDS thấp | Active Sensor threshold | `SENSOR_TDS_LOW` | Sensor model `TDS`, BELOW | `threshold_alert_configs.lower_threshold` | LOW default unless configured | Verify measurement and fish/plant balance; inspect nutrient process. |
| 22 / 19 Nhiệt độ không khí cao | Disabled (yellow) | `SENSOR_AIR_TEMPERATURE_HIGH` | Future semantic | Future canonical config | HIGH | Auto-completed only when activated. |
| 23 / 20 Độ ẩm không khí cao | Disabled (yellow) | `SENSOR_AIR_HUMIDITY_HIGH` | Future semantic | Future canonical config | MEDIUM | Auto-completed only when activated. |
| 24 / 21 Ánh sáng thấp nhiều ngày | Disabled (yellow) | `SENSOR_ILLUMINANCE_LOW_DURATION` | Future duration evaluator | Future canonical config | LOW_MEDIUM | Auto-completed only when activated. |

## Ambiguous source rows

### Excel row 10 / STT 7

- Original condition: actuator ON, voltage approximately 12 VDC, current
  approximately 0 A.
- Conflicting message: voltage 0 VDC and current 0 A.
- Interpretation: `ACTUATOR_NO_POWER` (0 V + 0 A), because row 9 already covers
  the same grow-bed pump at nominal voltage with zero current. This preserves
  two mutually exclusive electrical failure modes and prioritizes loss of power.

### Workbook Sensor threshold examples

The workbook gives pH 6/7.5 and water level 60% examples. They are treated only
as provisioning defaults. User-configured values in `threshold_alert_configs`
control evaluation and are snapshotted into an incident only as historical
evidence.

## Auto-completed operator wording

Messages avoid certainty where telemetry cannot prove a physical cause. They
use “có khả năng”, “cần kiểm tra”, and “hãy xác minh”. Unsafe prescriptive dosing
from the examples is not applied automatically: operators are asked to adjust
water chemistry gradually according to the installation procedure and remeasure.

