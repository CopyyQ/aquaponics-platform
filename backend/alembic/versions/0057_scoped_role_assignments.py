"""Add scoped role assignments and per-user permission overrides.

Revision ID: 0057
Revises: 0056
"""

import sqlalchemy as sa
from alembic import op

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None

ADMIN_PERMISSIONS = (
    "permissions.read", "permissions.create", "permissions.update", "permissions.delete",
    "roles.read", "roles.create", "roles.update", "roles.delete",
    "roles.permissions.read", "roles.permissions.update",
    "role_assignments.read", "role_assignments.update",
    "user_permissions.read", "user_permissions.update",
)

OWNER_WRITES = (
    "aquaponics_systems.manage_members",
    "sensors.thresholds.create", "sensors.thresholds.update", "sensors.thresholds.delete",
    "notifications.settings.update",
    "notifications.recipients.create", "notifications.recipients.update", "notifications.recipients.delete",
)

TECHNICIAN_WRITES = (
    "actuators.commands.create", "incidents.acknowledge", "incidents.resolve",
)


def upgrade() -> None:
    op.add_column("permissions", sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table(
        "role_assignments",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.BigInteger(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope_type", sa.String(32), nullable=False),
        sa.Column("scope_id", sa.BigInteger(), sa.ForeignKey("aquaponics_systems.id", ondelete="CASCADE")),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("(scope_type = 'GLOBAL' AND scope_id IS NULL) OR (scope_type = 'AQUAPONICS_SYSTEM' AND scope_id IS NOT NULL)", name="role_assignment_scope"),
        sa.UniqueConstraint("user_id", "role_id", "scope_type", "scope_id", name="uq_role_assignments_user_role_scope"),
    )
    op.create_index("ix_role_assignments_user_id", "role_assignments", ["user_id"])
    op.create_index("ix_role_assignments_role_id", "role_assignments", ["role_id"])
    op.create_index("ix_role_assignments_scope_id", "role_assignments", ["scope_id"])
    # PostgreSQL treats NULL values as distinct in a regular UNIQUE constraint.
    op.create_index("uq_role_assignments_global", "role_assignments", ["user_id", "role_id"], unique=True,
                    postgresql_where=sa.text("scope_type = 'GLOBAL'"))

    op.create_table(
        "user_permission_overrides",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope_type", sa.String(32), nullable=False),
        sa.Column("scope_id", sa.BigInteger(), sa.ForeignKey("aquaponics_systems.id", ondelete="CASCADE")),
        sa.Column("effect", sa.String(8), nullable=False),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("(scope_type = 'GLOBAL' AND scope_id IS NULL) OR (scope_type = 'AQUAPONICS_SYSTEM' AND scope_id IS NOT NULL)", name="user_permission_override_scope"),
        sa.CheckConstraint("effect IN ('ALLOW', 'DENY')", name="user_permission_override_effect"),
        sa.UniqueConstraint("user_id", "permission_id", "scope_type", "scope_id", name="uq_user_permission_overrides_user_permission_scope"),
    )
    op.create_index("ix_user_permission_overrides_user_id", "user_permission_overrides", ["user_id"])
    op.create_index("ix_user_permission_overrides_permission_id", "user_permission_overrides", ["permission_id"])
    op.create_index("ix_user_permission_overrides_scope_id", "user_permission_overrides", ["scope_id"])
    op.create_index("uq_user_permission_overrides_global", "user_permission_overrides", ["user_id", "permission_id"], unique=True,
                    postgresql_where=sa.text("scope_type = 'GLOBAL'"))

    bind = op.get_bind()
    for code in ADMIN_PERMISSIONS:
        resource, action = code.split(".", 1)
        bind.execute(sa.text("""
            INSERT INTO permissions (code, resource, action, enabled)
            VALUES (:code, :resource, :action, true) ON CONFLICT (code) DO UPDATE SET enabled = true
        """), {"code": code, "resource": resource, "action": action})
    bind.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.code = 'ADMIN' AND p.enabled = true ON CONFLICT DO NOTHING
    """))

    # Replace only the three built-in project bundles; custom roles are untouched.
    bind.execute(sa.text("DELETE FROM role_permissions rp USING roles r WHERE rp.role_id=r.id AND r.code IN ('OWNER','TECHNICIAN','VIEWER')"))
    read_condition = "p.action IN ('read','telemetry.read','thresholds.read','commands.read','readings.read','history.read','export') AND p.resource NOT IN ('users','permissions','roles','role_assignments','user_permissions')"
    bind.execute(sa.text(f"""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.code IN ('OWNER','TECHNICIAN','VIEWER') AND p.enabled = true AND {read_condition}
        ON CONFLICT DO NOTHING
    """))
    for role_code, codes in (("OWNER", OWNER_WRITES), ("TECHNICIAN", TECHNICIAN_WRITES)):
        bind.execute(sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = ANY(:codes)
            WHERE r.code=:role_code ON CONFLICT DO NOTHING
        """), {"role_code": role_code, "codes": list(codes)})

    bind.execute(sa.text("""
        INSERT INTO role_assignments (user_id, role_id, scope_type, scope_id)
        SELECT u.id, u.role_id, 'GLOBAL', NULL FROM users u
        WHERE u.role_id IS NOT NULL AND NOT EXISTS (
          SELECT 1 FROM role_assignments a WHERE a.user_id=u.id AND a.role_id=u.role_id
            AND a.scope_type='GLOBAL' AND a.scope_id IS NULL)
    """))
    bind.execute(sa.text("""
        INSERT INTO role_assignments (user_id, role_id, scope_type, scope_id, created_by)
        SELECT m.user_id, r.id, 'AQUAPONICS_SYSTEM', m.aquaponics_system_id, m.created_by
        FROM project_members m JOIN roles r ON r.code=m.role
        WHERE NOT EXISTS (SELECT 1 FROM role_assignments a WHERE a.user_id=m.user_id AND a.role_id=r.id
          AND a.scope_type='AQUAPONICS_SYSTEM' AND a.scope_id=m.aquaponics_system_id)
    """))
    bind.execute(sa.text("""
        INSERT INTO role_assignments (user_id, role_id, scope_type, scope_id)
        SELECT s.owner_user_id, r.id, 'AQUAPONICS_SYSTEM', s.id FROM aquaponics_systems s
        JOIN roles r ON r.code='OWNER'
        WHERE NOT EXISTS (SELECT 1 FROM role_assignments a WHERE a.user_id=s.owner_user_id AND a.role_id=r.id
          AND a.scope_type='AQUAPONICS_SYSTEM' AND a.scope_id=s.id)
    """))


def downgrade() -> None:
    raise RuntimeError("0057 changes live authorization state; restore a verified backup for rollback.")
