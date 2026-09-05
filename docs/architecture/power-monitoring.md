# Power monitoring

Power is a Sensor group on an existing Device, in canonical order: OUTPUT_VOLTAGE_V, INPUT_VOLTAGE_V, LOAD_CURRENT_A, INPUT_CURRENT_A, POWER_W and ENERGY_TOTAL_WH. The first five are GAUGE values and ENERGY_TOTAL_WH is the sole COUNTER. Optional nominal 12 V belongs in `device_templates.nominal_output_voltage_v`.

MQTT keeps `aquaponics/{device_code}/telemetry`; firmware sends sensor codes. The platform uses measured POWER_W and does not infer V×I. Counter deltas are summed by monotonic segment; a decrease starts a reset segment rather than producing negative consumption.

Project buckets are 1 minute/5 minutes/15 minutes/1 hour for `1h/6h/24h/1m`. Each bucket averages each Device first, then sums Device averages. Missing Device data produces `partial=true`, never an assumed 0 W.
