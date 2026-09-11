"""Add the default actuator model catalog."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

DEFAULT_MODELS = (
    ("FISH_TANK_PUMP", "Bơm hút bể cá", "Điều khiển bơm hút hoặc tuần hoàn nước tại bể cá.", 1),
    ("IRRIGATION_PUMP", "Bơm tưới", "Điều khiển bơm cấp nước cho hệ thống tưới.", 2),
    ("MIST_SYSTEM", "Phun sương", "Điều khiển hệ thống phun sương tạo ẩm môi trường.", 3),
    ("GROW_LIGHT", "Đèn chiếu sáng", "Điều khiển hệ thống đèn chiếu sáng cho khu vực trồng.", 4),
    ("ALARM_SIREN", "Còi cảnh báo", "Điều khiển còi cảnh báo khi hệ thống phát hiện sự cố.", 5),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("actuator_models")}
    if "sort_order" not in columns:
        op.add_column(
            "actuator_models",
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        )
    rows = sa.table(
        "actuator_models",
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("data_type", sa.String()),
        sa.column("default_state", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
    )
    for code, name, description, sort_order in DEFAULT_MODELS:
        bind.execute(
            pg_insert(rows)
            .values(
                code=code,
                name=name,
                description=description,
                data_type="BOOLEAN",
                default_state=False,
                is_active=True,
                sort_order=sort_order,
            )
            .on_conflict_do_nothing(index_elements=["code"])
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM actuator_models WHERE code IN "
            "('FISH_TANK_PUMP','IRRIGATION_PUMP','MIST_SYSTEM','GROW_LIGHT','ALARM_SIREN')"
        )
    )
    inspector = sa.inspect(bind)
    if "sort_order" in {column["name"] for column in inspector.get_columns("actuator_models")}:
        op.drop_column("actuator_models", "sort_order")
