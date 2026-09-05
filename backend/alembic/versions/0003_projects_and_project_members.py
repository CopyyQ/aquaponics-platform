"""Move device ownership and viewer access to projects.

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if {
        "projects", "project_members"
    }.issubset(inspector.get_table_names()) and "project_id" in {
        column["name"] for column in inspector.get_columns("devices")
    }:
        return
    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_owner_user_id", "projects", ["owner_user_id"])
    op.create_index("ix_projects_code", "projects", ["code"], unique=True)
    op.create_index("ix_projects_is_deleted", "projects", ["is_deleted"])

    # Một project mặc định cho mỗi owner hiện có; mọi device của owner đều được giữ nguyên.
    op.execute(
        """
        INSERT INTO projects (owner_user_id, code, name, description, is_deleted)
        SELECT u.id, 'PROJECT-' || u.id, 'Dự án của ' || u.full_name,
               'Dự án được tạo tự động khi chuyển đổi mô hình dữ liệu', false
        FROM users u
        WHERE EXISTS (SELECT 1 FROM devices d WHERE d.owner_user_id = u.id)
        """
    )
    # Dữ liệu cũ không có owner được gán vào project phục hồi của Admin/Owner đầu tiên.
    op.execute(
        """
        INSERT INTO projects (owner_user_id, code, name, description, is_deleted)
        SELECT u.id, 'PROJECT-RECOVERED', 'Thiết bị chưa phân loại',
               'Project phục hồi cho thiết bị cũ chưa có chủ sở hữu', false
        FROM users u
        WHERE EXISTS (SELECT 1 FROM devices WHERE owner_user_id IS NULL)
          AND u.id = (SELECT id FROM users WHERE is_deleted = false ORDER BY
             CASE system_role WHEN 'OWNER' THEN 0 WHEN 'ADMIN' THEN 1 ELSE 2 END, id LIMIT 1)
        """
    )
    op.add_column("devices", sa.Column("project_id", sa.BigInteger(), nullable=True))
    op.add_column("devices", sa.Column("location", sa.String(length=255), nullable=True))
    op.execute(
        """
        UPDATE devices d SET project_id = p.id
        FROM projects p
        WHERE p.owner_user_id = d.owner_user_id AND p.code = 'PROJECT-' || d.owner_user_id
        """
    )
    op.execute(
        """
        UPDATE devices SET project_id = (SELECT id FROM projects WHERE code = 'PROJECT-RECOVERED')
        WHERE project_id IS NULL
        """
    )
    op.alter_column("devices", "project_id", nullable=False)
    op.create_foreign_key(
        "fk_devices_project_id_projects", "devices", "projects", ["project_id"], ["id"],
        ondelete="RESTRICT"
    )
    op.create_index("ix_devices_project_id", "devices", ["project_id"], unique=False)

    op.create_table(
        "project_members",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="VIEWER", nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])
    op.execute(
        """
        INSERT INTO project_members (project_id, user_id, role, created_by, created_at)
        SELECT DISTINCT d.project_id, dm.user_id, 'VIEWER', dm.created_by, min(dm.created_at)
        FROM device_members dm JOIN devices d ON d.id = dm.device_id
        GROUP BY d.project_id, dm.user_id, dm.created_by
        ON CONFLICT (project_id, user_id) DO NOTHING
        """
    )
    op.drop_table("device_members")
    op.drop_index("ix_devices_owner_user_id", table_name="devices")
    op.drop_constraint("fk_devices_owner_user_id_users", "devices", type_="foreignkey")
    op.drop_column("devices", "owner_user_id")
    op.add_column("users", sa.Column("token_version", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.add_column("devices", sa.Column("owner_user_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_devices_owner_user_id_users", "devices", "users", ["owner_user_id"], ["id"],
        ondelete="SET NULL"
    )
    op.create_index("ix_devices_owner_user_id", "devices", ["owner_user_id"])
    op.execute(
        "UPDATE devices d SET owner_user_id = p.owner_user_id FROM projects p WHERE p.id = d.project_id"
    )
    op.create_table(
        "device_members",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("device_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="VIEWER", nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "user_id", name="uq_device_members_device_user"),
    )
    op.execute(
        """
        INSERT INTO device_members (device_id, user_id, role, created_by, created_at)
        SELECT d.id, pm.user_id, pm.role, pm.created_by, pm.created_at
        FROM project_members pm JOIN devices d ON d.project_id = pm.project_id
        """
    )
    op.drop_table("project_members")
    op.drop_index("ix_devices_project_id", table_name="devices")
    op.drop_constraint("fk_devices_project_id_projects", "devices", type_="foreignkey")
    op.drop_column("devices", "location")
    op.drop_column("devices", "project_id")
    op.drop_table("projects")
    op.drop_column("users", "token_version")
