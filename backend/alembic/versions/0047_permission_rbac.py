"""Add database-backed roles and permissions."""

from alembic import op
import sqlalchemy as sa

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("users.read", "users", "read"), ("users.create", "users", "create"),
    ("users.update", "users", "update"), ("users.delete", "users", "delete"),
    ("users.force_logout", "users", "force_logout"), ("users.set_password", "users", "set_password"),
    ("users.lock", "users", "lock"), ("users.unlock", "users", "unlock"),
    ("aquaponics_systems.read", "aquaponics_systems", "read"),
    ("aquaponics_systems.create", "aquaponics_systems", "create"),
    ("aquaponics_systems.update", "aquaponics_systems", "update"),
    ("aquaponics_systems.delete", "aquaponics_systems", "delete"),
    ("aquaponics_systems.manage_members", "aquaponics_systems", "manage_members"),
    ("aquaponics_systems.read_all", "aquaponics_systems", "read_all"),
    ("aquaponics_systems.manage_all", "aquaponics_systems", "manage_all"),
    ("devices.read", "devices", "read"), ("devices.create", "devices", "create"),
    ("devices.update", "devices", "update"), ("devices.delete", "devices", "delete"),
    ("sensors.read", "sensors", "read"), ("sensors.create", "sensors", "create"),
    ("sensors.update", "sensors", "update"), ("sensors.delete", "sensors", "delete"),
    ("sensors.telemetry.read", "sensors", "telemetry.read"),
    ("sensors.thresholds.read", "sensors", "thresholds.read"),
    ("sensors.thresholds.create", "sensors", "thresholds.create"),
    ("sensors.thresholds.update", "sensors", "thresholds.update"),
    ("sensors.thresholds.delete", "sensors", "thresholds.delete"),
    ("actuators.read", "actuators", "read"), ("actuators.create", "actuators", "create"),
    ("actuators.update", "actuators", "update"), ("actuators.delete", "actuators", "delete"),
    ("actuators.commands.read", "actuators", "commands.read"),
    ("actuators.commands.create", "actuators", "commands.create"),
    ("actuators.readings.read", "actuators", "readings.read"),
    ("actuators.thresholds.read", "actuators", "thresholds.read"),
    ("actuators.thresholds.create", "actuators", "thresholds.create"),
    ("actuators.thresholds.update", "actuators", "thresholds.update"),
    ("actuators.thresholds.delete", "actuators", "thresholds.delete"),
    ("sensor_models.read", "sensor_models", "read"), ("sensor_models.create", "sensor_models", "create"),
    ("sensor_models.update", "sensor_models", "update"), ("sensor_models.delete", "sensor_models", "delete"),
    ("actuator_models.read", "actuator_models", "read"), ("actuator_models.create", "actuator_models", "create"),
    ("actuator_models.update", "actuator_models", "update"), ("actuator_models.delete", "actuator_models", "delete"),
    ("device_templates.read", "device_templates", "read"), ("device_templates.create", "device_templates", "create"),
    ("device_templates.update", "device_templates", "update"), ("device_templates.delete", "device_templates", "delete"),
    ("monitoring.read", "monitoring", "read"), ("incidents.read", "incidents", "read"),
    ("incidents.acknowledge", "incidents", "acknowledge"), ("incidents.resolve", "incidents", "resolve"),
    ("notifications.settings.read", "notifications", "settings.read"),
    ("notifications.settings.update", "notifications", "settings.update"),
    ("notifications.recipients.read", "notifications", "recipients.read"),
    ("notifications.recipients.create", "notifications", "recipients.create"),
    ("notifications.recipients.update", "notifications", "recipients.update"),
    ("notifications.recipients.delete", "notifications", "recipients.delete"),
    ("notifications.recipients.test", "notifications", "recipients.test"),
    ("notifications.history.read", "notifications", "history.read"),
    ("mqtt_config.export", "mqtt_config", "export"), ("scada.read", "scada", "read"),
    ("scada.update", "scada", "update"), ("activities.read", "activities", "read"),
)


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("code", sa.String(120), nullable=False, unique=True), sa.Column("resource", sa.String(80), nullable=False),
        sa.Column("action", sa.String(80), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("role_id", sa.BigInteger(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )
    op.add_column("users", sa.Column("role_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_users_role_id_roles", "users", "roles", ["role_id"], ["id"], ondelete="RESTRICT")
    bind = op.get_bind()
    for code, name in (("ADMIN", "Administrator"), ("OWNER", "System Owner"), ("TECHNICIAN", "Technician"), ("VIEWER", "Viewer")):
        bind.execute(sa.text("INSERT INTO roles (code,name,is_system,enabled) VALUES (:code,:name,true,true) ON CONFLICT (code) DO NOTHING"), {"code": code, "name": name})
    for code, resource, action in PERMISSIONS:
        bind.execute(sa.text("INSERT INTO permissions (code,resource,action) VALUES (:code,:resource,:action) ON CONFLICT (code) DO NOTHING"), {"code": code, "resource": resource, "action": action})
    bind.execute(sa.text("UPDATE users u SET role_id = r.id FROM roles r WHERE r.code = u.system_role::text AND u.role_id IS NULL"))
    bind.execute(sa.text("UPDATE users SET role_id = (SELECT id FROM roles WHERE code='VIEWER') WHERE role_id IS NULL"))
    bind.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.code = 'ADMIN' ON CONFLICT DO NOTHING
    """))
    bind.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r JOIN permissions p ON
          (r.code='VIEWER' AND p.resource NOT IN ('users') AND p.action IN ('read','telemetry.read','thresholds.read','commands.read','readings.read','history.read','export'))
          OR (r.code IN ('OWNER','TECHNICIAN') AND p.resource NOT IN ('users') AND p.action NOT IN ('read_all','manage_all'))
        ON CONFLICT DO NOTHING
    """))


def downgrade() -> None:
    raise RuntimeError("0047 is a forward authorization migration; restore a verified backup for rollback.")
