"""Idempotent Phase-B conversion of legacy directional thresholds to AlertRule scenarios."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.engine import Connection


@dataclass(frozen=True)
class LegacyConversionReport:
    legacy_rows: int = 0
    created_scenarios: int = 0
    existing_scenarios: int = 0
    unrepresentable_directions: int = 0


configs = sa.table("threshold_alert_configs",
    sa.column("id", sa.BigInteger), sa.column("sensor_id", sa.BigInteger),
    sa.column("actuator_id", sa.BigInteger), sa.column("metric_type", sa.String),
    sa.column("enabled", sa.Boolean), sa.column("lower_threshold", sa.Float),
    sa.column("upper_threshold", sa.Float), sa.column("below_risk_level", sa.String),
    sa.column("above_risk_level", sa.String), sa.column("below_message", sa.Text),
    sa.column("above_message", sa.Text), sa.column("below_consequence", sa.Text),
    sa.column("above_consequence", sa.Text), sa.column("below_recommended_actions", sa.Text),
    sa.column("above_recommended_actions", sa.Text), sa.column("delay_seconds", sa.Integer))
rules = sa.table("alert_rules", sa.column("id", sa.BigInteger), sa.column("public_id", PGUUID(as_uuid=True)),
    sa.column("code", sa.String), sa.column("name", sa.String), sa.column("target_type", sa.String),
    sa.column("evaluator_type", sa.String), sa.column("is_enabled", sa.Boolean),
    sa.column("current_revision_id", sa.BigInteger), sa.column("retired_at", sa.DateTime(timezone=True)))
revisions = sa.table("alert_rule_revisions", sa.column("id", sa.BigInteger), sa.column("rule_id", sa.BigInteger),
    sa.column("revision", sa.Integer), sa.column("business_risk_level", sa.String),
    sa.column("condition_schema_version", sa.Integer), sa.column("condition_config", JSONB),
    sa.column("message_template", sa.Text), sa.column("consequence", sa.Text),
    sa.column("recommended_action", sa.Text), sa.column("source_reference", sa.String),
    sa.column("source_order", sa.Integer), sa.column("status", sa.String),
    sa.column("created_by", sa.BigInteger), sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("published_by", sa.BigInteger), sa.column("published_at", sa.DateTime(timezone=True)))
sensor_bindings = sa.table("alert_rule_sensor_overrides", sa.column("rule_id", sa.BigInteger),
    sa.column("sensor_id", sa.BigInteger), sa.column("config", JSONB), sa.column("is_enabled", sa.Boolean))
actuator_bindings = sa.table("alert_rule_actuator_overrides", sa.column("rule_id", sa.BigInteger),
    sa.column("actuator_id", sa.BigInteger), sa.column("config", JSONB), sa.column("is_enabled", sa.Boolean))


def convert_legacy_threshold_configs(connection: Connection) -> LegacyConversionReport:
    """Convert all representable rows in the caller's transaction.

    The transaction-scoped advisory lock makes concurrent/rerun behavior deterministic.
    Rule codes are stable audit keys; legacy rows remain untouched.
    """
    connection.execute(sa.text("SELECT pg_advisory_xact_lock(hashtext('legacy_threshold_to_alert_scenarios_v1'))"))
    rows = connection.execute(sa.select(configs).order_by(configs.c.id)).mappings().all()
    created = existing = unrepresentable = 0
    for row in rows:
        for direction in ("BELOW", "ABOVE"):
            threshold = row["lower_threshold"] if direction == "BELOW" else row["upper_threshold"]
            if threshold is None:
                continue
            prefix = "below" if direction == "BELOW" else "above"
            risk = row[f"{prefix}_risk_level"]
            if risk is None:
                # The legacy runtime also refused to open an incident without directional risk.
                unrepresentable += 1
                continue
            code = f"LEGACY_THRESHOLD_{row['id']}_{direction}"
            if connection.scalar(sa.select(rules.c.id).where(rules.c.code == code)) is not None:
                existing += 1
                continue
            target_type = "SENSOR" if row["sensor_id"] is not None else "ACTUATOR"
            operator = "LT" if direction == "BELOW" else "GT"
            audit = {"source": "threshold_alert_configs", "config_id": row["id"],
                     "metric_type": row["metric_type"], "direction": direction}
            if target_type == "SENSOR":
                evaluator_type = "THRESHOLD_DURATION" if row["delay_seconds"] else "THRESHOLD"
                condition = {"operator": operator, "value": threshold,
                             "duration_seconds": row["delay_seconds"], "legacy_conversion": audit}
            else:
                evaluator_type = "MULTI_CONDITION"
                field = "voltage" if row["metric_type"] == "VOLTAGE" else "current"
                condition = {"logic": "AND", "reported_state": None, "voltage": None, "current": None,
                             "duration_seconds": row["delay_seconds"], "legacy_conversion": audit}
                condition[field] = {"operator": operator, "value": threshold}
            now = datetime.now(UTC)
            rule_id = connection.execute(rules.insert().values(public_id=uuid4(), code=code,
                name=f"Ngưỡng {row['metric_type']} {'dưới' if direction == 'BELOW' else 'trên'} (legacy #{row['id']})",
                target_type=target_type, evaluator_type=evaluator_type,
                is_enabled=bool(row["enabled"]), retired_at=None).returning(rules.c.id)).scalar_one()
            revision_id = connection.execute(revisions.insert().values(rule_id=rule_id, revision=1,
                business_risk_level=risk, condition_schema_version=1, condition_config=condition,
                message_template=row[f"{prefix}_message"], consequence=row[f"{prefix}_consequence"],
                recommended_action=row[f"{prefix}_recommended_actions"],
                source_reference=f"threshold_alert_configs:{row['id']}:{direction}", source_order=0,
                status="PUBLISHED", created_by=None, created_at=now, published_by=None,
                published_at=now).returning(revisions.c.id)).scalar_one()
            connection.execute(rules.update().where(rules.c.id == rule_id).values(current_revision_id=revision_id))
            binding_values = {"rule_id": rule_id, "config": {"legacy_conversion": audit}, "is_enabled": True}
            if target_type == "SENSOR":
                connection.execute(sensor_bindings.insert().values(sensor_id=row["sensor_id"], **binding_values))
            else:
                connection.execute(actuator_bindings.insert().values(actuator_id=row["actuator_id"], **binding_values))
            created += 1
    return LegacyConversionReport(len(rows), created, existing, unrepresentable)
