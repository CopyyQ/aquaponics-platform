"""Add stable actuator identity and soft-removal metadata."""

from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("actuators")
    }
    additions = {
        "sequence_number": sa.Column("sequence_number", sa.Integer(), nullable=True),
        "removed_at": sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        "removed_by_user_id": sa.Column("removed_by_user_id", sa.BigInteger(), nullable=True),
        "removed_reason": sa.Column("removed_reason", sa.Text(), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("actuators", column)

    op.execute(
        sa.text(
            """
            WITH numbered AS (
                SELECT
                    actuators.id,
                    ROW_NUMBER() OVER (
                        PARTITION BY devices.project_id, actuators.actuator_model_id
                        ORDER BY actuators.created_at, actuators.id
                    ) AS sequence_number
                FROM actuators
                JOIN devices ON devices.id = actuators.device_id
            )
            UPDATE actuators
            SET sequence_number = numbered.sequence_number
            FROM numbered
            WHERE numbered.id = actuators.id
              AND actuators.sequence_number IS NULL
            """
        )
    )
    op.alter_column("actuators", "sequence_number", nullable=False)

    inspector = sa.inspect(bind)
    foreign_keys = {
        foreign_key.get("name")
        for foreign_key in inspector.get_foreign_keys("actuators")
    }
    if "fk_actuators_removed_by_user_id_users" not in foreign_keys:
        op.create_foreign_key(
            "fk_actuators_removed_by_user_id_users",
            "actuators",
            "users",
            ["removed_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    unique_constraints = {
        constraint.get("name")
        for constraint in inspector.get_unique_constraints("actuators")
    }
    if "uq_actuators_code" not in unique_constraints:
        op.create_unique_constraint("uq_actuators_code", "actuators", ["code"])


def downgrade() -> None:
    op.drop_constraint("uq_actuators_code", "actuators", type_="unique")
    op.drop_constraint(
        "fk_actuators_removed_by_user_id_users",
        "actuators",
        type_="foreignkey",
    )
    for name in (
        "removed_reason",
        "removed_by_user_id",
        "removed_at",
        "sequence_number",
    ):
        op.drop_column("actuators", name)
