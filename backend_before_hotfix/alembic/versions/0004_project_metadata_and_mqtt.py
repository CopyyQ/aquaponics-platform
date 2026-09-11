"""Complete project metadata required by the MQTT project model.

Revision ID: 0004
Revises: 0003
"""

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    project_columns = {column["name"] for column in inspector.get_columns("projects")}
    member_columns = {column["name"] for column in inspector.get_columns("project_members")}
    sensor_columns = {column["name"] for column in inspector.get_columns("sensors")}
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    project_status = sa.Enum("ACTIVE", "INACTIVE", "ARCHIVED", name="project_status")
    project_status.create(op.get_bind(), checkfirst=True)
    if "location" not in project_columns:
        op.add_column("projects", sa.Column("location", sa.String(length=255), nullable=True))
    if "status" not in project_columns:
        op.add_column("projects", sa.Column("status", project_status, server_default="ACTIVE", nullable=False))
    project_indexes = {index["name"] for index in inspector.get_indexes("projects")}
    if "ix_projects_status" not in project_indexes:
        op.create_index("ix_projects_status", "projects", ["status"])
    if "updated_at" not in member_columns:
        op.add_column("project_members", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    if "installation_location" not in sensor_columns:
        op.add_column("sensors", sa.Column("installation_location", sa.String(length=255), nullable=True))
    sensor_indexes = {index["name"] for index in inspector.get_indexes("sensors")}
    if "ix_sensors_device_id" not in sensor_indexes:
        op.create_index("ix_sensors_device_id", "sensors", ["device_id"])
    if "password_changed_at" not in user_columns:
        op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
    op.drop_index("ix_sensors_device_id", table_name="sensors")
    op.drop_column("sensors", "installation_location")
    op.drop_column("project_members", "updated_at")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_column("projects", "status")
    op.drop_column("projects", "location")
    sa.Enum(name="project_status").drop(op.get_bind(), checkfirst=True)
