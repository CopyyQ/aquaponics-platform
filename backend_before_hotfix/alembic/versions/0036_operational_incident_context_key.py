"""Make active OperationalIncident identity independent of nullable rule_id.

Revision ID: 0036
Revises: 0035
"""

from alembic import op
import sqlalchemy as sa

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None

_ACTIVE = "status IN ('PENDING','OPEN','ACKNOWLEDGED','NORMALIZED')"


def upgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(sa.text(f"""
        SELECT project_id, context_key, count(*)
        FROM operational_incidents
        WHERE {_ACTIVE}
        GROUP BY project_id, context_key
        HAVING count(*) > 1
    """)).fetchall()
    if duplicates:
        raise RuntimeError(
            "Cannot add canonical active incident identity; duplicate active "
            f"project/context rows exist: {duplicates[:10]!r}. Resolve them explicitly."
        )
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("operational_incidents")}
    if "uq_active_operational_incident_project_context" not in indexes:
        op.create_index(
            "uq_active_operational_incident_project_context",
            "operational_incidents",
            ["project_id", "context_key"],
            unique=True,
            postgresql_where=sa.text(_ACTIVE),
        )


def downgrade() -> None:
    op.drop_index("uq_active_operational_incident_project_context", table_name="operational_incidents")
