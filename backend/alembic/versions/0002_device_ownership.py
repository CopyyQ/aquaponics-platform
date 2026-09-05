"""Add per-user device ownership and viewer memberships.

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    # Fresh databases created by the historical 0001 module use current ORM
    # metadata and already contain the final Project schema.
    if "projects" in inspector.get_table_names() and "project_id" in {
        column["name"] for column in inspector.get_columns("devices")
    } and "token_version" in {column["name"] for column in inspector.get_columns("users")}:
        return
    op.drop_index("uq_active_owner", table_name="users")
    op.add_column("devices", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_devices_owner_user_id_users",
        "devices",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_devices_owner_user_id", "devices", ["owner_user_id"])
    op.create_table(
        "device_members",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("device_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="VIEWER", nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role = 'VIEWER'", name="ck_device_members_device_member_viewer_role"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "user_id", name="uq_device_members_device_user"),
    )
    op.create_index("ix_device_members_device_id", "device_members", ["device_id"])
    op.create_index("ix_device_members_user_id", "device_members", ["user_id"])

    # Chỉ backfill khi có đúng một OWNER đang hoạt động; trường hợp mơ hồ giữ NULL.
    op.execute(
        """
        UPDATE devices
        SET owner_user_id = candidate.id
        FROM (
            SELECT min(id) AS id
            FROM users
            WHERE system_role = 'OWNER' AND status = 'ACTIVE' AND is_deleted = false
            HAVING count(*) = 1
        ) AS candidate
        WHERE devices.owner_user_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_table("device_members")
    op.drop_index("ix_devices_owner_user_id", table_name="devices")
    op.drop_constraint("fk_devices_owner_user_id_users", "devices", type_="foreignkey")
    op.drop_column("devices", "owner_user_id")
    op.create_index(
        "uq_active_owner",
        "users",
        ["system_role"],
        unique=True,
        postgresql_where=sa.text(
            "system_role = 'OWNER' AND status = 'ACTIVE' AND is_deleted = false"
        ),
    )
