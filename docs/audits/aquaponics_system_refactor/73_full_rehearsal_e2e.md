# Rehearsal API acceptance

The PostgreSQL-backed ASGI acceptance test creates one Aquaponics System, one Device, two Sensors, and two Actuators through the canonical API, then reads the device detail and verifies both component collections. The permission suite verifies session permissions are database-backed and a permission can be revoked without changing a JWT. All 27 rehearsal tests passed at revision 0050.
