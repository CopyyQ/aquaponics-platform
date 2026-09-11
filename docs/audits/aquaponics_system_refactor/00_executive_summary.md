# Aquaponics System refactor

The development database remains at revision 0045. A fresh custom-format backup was created before 0046 work. The isolated rehearsal database successfully applied 0046: the `projects` table became `aquaponics_systems`, all domain foreign-key columns became `aquaponics_system_id`, the three deterministic 0045 actuator clones were re-merged, and the topology triggers were removed.

The dev apply gate is intentionally not open yet: canonical API, frontend migration, and full regression validation remain in progress.
