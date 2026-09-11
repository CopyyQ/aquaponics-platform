# Retired feedback runtime inventory

No active Python module under `backend/app` or `backend/scripts` references the retired actuator-feedback binding runtime. Revision 0048 preserves old rows only in clearly named `legacy_*` archive tables; production reads and alert evaluation use the canonical actuator and threshold-alert models.
