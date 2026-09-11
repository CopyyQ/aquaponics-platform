"""Complete actuator electrical feedback and alert applicability.

Revision ID: 0032
Revises: 0031
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    definition_table = "actuator_model_feedback_definitions"
    definition_columns = {item["name"] for item in inspector.get_columns(definition_table)}
    if "default_lower_threshold" not in definition_columns:
        op.add_column(definition_table, sa.Column("default_lower_threshold", sa.Float(), nullable=True))
    if "default_upper_threshold" not in definition_columns:
        op.add_column(definition_table, sa.Column("default_upper_threshold", sa.Float(), nullable=True))
    inspector = sa.inspect(bind)
    definition_checks = {item["name"]: str(item.get("sqltext") or "") for item in inspector.get_check_constraints(definition_table)}
    if not any("default_lower_threshold" in sqltext and "default_upper_threshold" in sqltext for sqltext in definition_checks.values()):
        op.create_check_constraint("threshold_order", definition_table, "default_lower_threshold IS NULL OR default_upper_threshold IS NULL OR default_lower_threshold < default_upper_threshold")
    definition_role_check = next(((name, sqltext) for name, sqltext in definition_checks.items() if "feedback_role" in sqltext), None)
    if definition_role_check is None or "SUPPLY_VOLTAGE" not in definition_role_check[1]:
        if definition_role_check is not None:
            op.drop_constraint(op.f(definition_role_check[0]), definition_table, type_="check")
        op.create_check_constraint("role_allowed", definition_table, "feedback_role IN ('SUPPLY_VOLTAGE','RUNNING_CURRENT')")

    binding_table = "actuator_feedback_bindings"
    binding_columns = {item["name"] for item in inspector.get_columns(binding_table)}
    if "lower_threshold" not in binding_columns:
        op.add_column(binding_table, sa.Column("lower_threshold", sa.Float(), nullable=True))
    if "upper_threshold" not in binding_columns:
        op.add_column(binding_table, sa.Column("upper_threshold", sa.Float(), nullable=True))
    inspector = sa.inspect(bind)
    binding_checks = {item["name"]: str(item.get("sqltext") or "") for item in inspector.get_check_constraints(binding_table)}
    if not any("lower_threshold" in sqltext and "upper_threshold" in sqltext for sqltext in binding_checks.values()):
        op.create_check_constraint("feedback_binding_threshold_order", binding_table, "lower_threshold IS NULL OR upper_threshold IS NULL OR lower_threshold < upper_threshold")
    binding_role_check = next(((name, sqltext) for name, sqltext in binding_checks.items() if "feedback_role" in sqltext), None)
    if binding_role_check is None or "SUPPLY_VOLTAGE" not in binding_role_check[1]:
        if binding_role_check is not None:
            op.drop_constraint(op.f(binding_role_check[0]), binding_table, type_="check")
        op.create_check_constraint("actuator_feedback_role_allowed", binding_table, "feedback_role IN ('SUPPLY_VOLTAGE','RUNNING_CURRENT')")

    inspector = sa.inspect(bind)
    if "alert_rule_sensor_models" not in inspector.get_table_names():
        op.create_table(
        "alert_rule_sensor_models",
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column("sensor_model_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sensor_model_id"], ["sensor_models.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("rule_id", "sensor_model_id"),
        )
        op.create_index("ix_alert_rule_sensor_models_sensor_model_id", "alert_rule_sensor_models", ["sensor_model_id"])
    if "alert_rule_actuator_models" not in inspector.get_table_names():
        op.create_table(
        "alert_rule_actuator_models",
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column("actuator_model_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actuator_model_id"], ["actuator_models.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("rule_id", "actuator_model_id"),
        )
        op.create_index("ix_alert_rule_actuator_models_actuator_model_id", "alert_rule_actuator_models", ["actuator_model_id"])

    # Preserve the existing applicability expressed through profiles.
    op.execute(sa.text("""
        INSERT INTO alert_rule_sensor_models (rule_id, sensor_model_id)
        SELECT DISTINCT p.rule_id, m.sensor_model_id
        FROM alert_rule_profiles p
        JOIN alert_rule_sensor_model_profiles m ON m.profile_id = p.id
        ON CONFLICT DO NOTHING
    """))
    op.execute(sa.text("""
        INSERT INTO alert_rule_actuator_models (rule_id, actuator_model_id)
        SELECT DISTINCT p.rule_id, m.actuator_model_id
        FROM alert_rule_profiles p
        JOIN alert_rule_actuator_model_profiles m ON m.profile_id = p.id
        ON CONFLICT DO NOTHING
    """))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "alert_rule_actuator_models" in table_names:
        op.drop_table("alert_rule_actuator_models")
    if "alert_rule_sensor_models" in table_names:
        op.drop_table("alert_rule_sensor_models")

    binding_table = "actuator_feedback_bindings"
    binding_checks = {item["name"]: str(item.get("sqltext") or "") for item in inspector.get_check_constraints(binding_table)}
    for name, sqltext in binding_checks.items():
        if "feedback_role" in sqltext or ("lower_threshold" in sqltext and "upper_threshold" in sqltext):
            op.drop_constraint(op.f(name), binding_table, type_="check")
    op.create_check_constraint("actuator_feedback_role_allowed", binding_table, "feedback_role IN ('RUNNING_CURRENT')")
    binding_columns = {item["name"] for item in inspector.get_columns(binding_table)}
    if "upper_threshold" in binding_columns:
        op.drop_column(binding_table, "upper_threshold")
    if "lower_threshold" in binding_columns:
        op.drop_column(binding_table, "lower_threshold")

    definition_table = "actuator_model_feedback_definitions"
    definition_checks = {item["name"]: str(item.get("sqltext") or "") for item in inspector.get_check_constraints(definition_table)}
    for name, sqltext in definition_checks.items():
        if "feedback_role" in sqltext or ("default_lower_threshold" in sqltext and "default_upper_threshold" in sqltext):
            op.drop_constraint(op.f(name), definition_table, type_="check")
    op.create_check_constraint("role_allowed", definition_table, "feedback_role IN ('RUNNING_CURRENT')")
    definition_columns = {item["name"] for item in inspector.get_columns(definition_table)}
    if "default_upper_threshold" in definition_columns:
        op.drop_column(definition_table, "default_upper_threshold")
    if "default_lower_threshold" in definition_columns:
        op.drop_column(definition_table, "default_lower_threshold")
