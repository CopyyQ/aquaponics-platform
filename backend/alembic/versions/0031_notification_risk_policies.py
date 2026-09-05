"""Add normalized notification policies per business-risk level.

Revision ID: 0031
Revises: 0030
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table = "project_notification_risk_policies"
    if table not in inspector.get_table_names():
        op.create_table(
            table,
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
            sa.Column("project_id", sa.BigInteger(), nullable=False),
            sa.Column("risk_level", sa.String(30), nullable=False),
            sa.Column("telegram_enabled", sa.Boolean(), nullable=False),
            sa.Column("notify_on_open", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("notify_on_escalation", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("notify_on_recovery", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("notify_on_resolved", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("reminder_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("initial_reminder_seconds", sa.Integer(), server_default="0", nullable=False),
            sa.Column("repeat_interval_seconds", sa.Integer(), server_default="0", nullable=False),
            sa.Column("max_reminders", sa.Integer(), server_default="0", nullable=False),
            sa.Column("stop_reminders_on_ack", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("project_id", "risk_level", name="uq_project_notification_risk_policy"),
            sa.CheckConstraint("risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')", name="risk_level_allowed"),
            sa.CheckConstraint("initial_reminder_seconds >= 0", name="initial_nonnegative"),
            sa.CheckConstraint("repeat_interval_seconds >= 0", name="repeat_nonnegative"),
            sa.CheckConstraint("max_reminders >= 0", name="max_reminders_nonnegative"),
        )
        op.create_index("ix_project_notification_risk_policies_project_id", table, ["project_id"])

    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("notification_outbox")}
    if "skip_reason" not in columns:
        op.add_column("notification_outbox", sa.Column("skip_reason", sa.String(120)))

    # Existing projects retain their master/event/risk choices. Reminder cadence is
    # translated from the legacy interval when present; otherwise platform defaults apply.
    op.execute(sa.text("""
        INSERT INTO project_notification_risk_policies
          (project_id, risk_level, telegram_enabled, notify_on_open,
           notify_on_escalation, notify_on_recovery, notify_on_resolved,
           reminder_enabled, initial_reminder_seconds, repeat_interval_seconds,
           max_reminders, stop_reminders_on_ack)
        SELECT s.project_id, v.risk_level,
          CASE v.risk_level
            WHEN 'EXTREME' THEN s.risk_extreme_enabled
            WHEN 'VERY_HIGH' THEN s.risk_very_high_enabled
            WHEN 'HIGH' THEN s.risk_high_enabled
            WHEN 'MEDIUM' THEN s.risk_medium_enabled
            WHEN 'LOW_MEDIUM' THEN s.risk_low_medium_enabled
            ELSE s.risk_low_enabled END,
          s.notify_alert_opened, s.notify_alert_escalated,
          s.notify_alert_recovered, s.notify_alert_resolved,
          CASE WHEN s.notify_alert_reminder THEN true ELSE v.reminder_enabled END,
          COALESCE(s.reminder_interval_minutes * 60, v.initial_seconds),
          COALESCE(s.reminder_interval_minutes * 60, v.repeat_seconds),
          v.max_reminders, true
        FROM project_notification_settings s
        CROSS JOIN (VALUES
          ('EXTREME', true, 300, 600, 4),
          ('VERY_HIGH', true, 900, 1800, 3),
          ('HIGH', true, 1800, 3600, 2),
          ('MEDIUM', false, 1800, 3600, 0),
          ('LOW_MEDIUM', false, 3600, 7200, 0),
          ('LOW', false, 3600, 7200, 0)
        ) AS v(risk_level, reminder_enabled, initial_seconds, repeat_seconds, max_reminders)
        ON CONFLICT (project_id, risk_level) DO NOTHING
    """))


def downgrade() -> None:
    op.drop_column("notification_outbox", "skip_reason")
    op.drop_index("ix_project_notification_risk_policies_project_id", table_name="project_notification_risk_policies")
    op.drop_table("project_notification_risk_policies")
