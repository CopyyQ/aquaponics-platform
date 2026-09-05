"""Close operational alert evaluator, catalog and revision integrity gaps."""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op


revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


PUBLISHED_RULE_CODES = (
    "FISH_TANK_DO_LOW",
    "WATER_PH_OUT_OF_RANGE",
    "NITRITE_HIGH",
    "TDS_LOW",
    "AIR_TEMPERATURE_HIGH",
)

CANONICAL_SENSOR_PROFILES = (
    ("FISH_TANK_DO_LOW", "DO"),
    ("WATER_PH_OUT_OF_RANGE", "PH"),
    ("TDS_LOW", "TDS"),
    ("AIR_TEMPERATURE_HIGH", "AIR_TEMPERATURE"),
)

INCOMPLETE_TYPED_CONFIGS = {
    "MAIN_PUMP_FLOW_LOW": {
        "unit": None,
        "baseline_source": None,
        "baseline_value": None,
        "deviation_operator": None,
        "deviation_percent": None,
        "minimum_samples": None,
        "window_seconds": None,
        "severity": "WARNING",
    },
    "AMMONIA_ABNORMAL": {
        "unit": None,
        "direction": None,
        "window_duration_seconds": None,
        "minimum_samples": None,
        "minimum_delta": None,
        "severity": "WARNING",
    },
    "ENVIRONMENT_LIGHT_LOW_LONG_TERM": {
        "unit": "lux",
        "condition": "LT",
        "threshold": None,
        "window_duration_seconds": None,
        "minimum_coverage": None,
        "minimum_samples": None,
        "aggregation": None,
        "severity": "WARNING",
    },
    "TDS_LOW_LONG_TERM": {
        "unit": "ppm",
        "condition": "LT",
        "threshold": 150,
        "window_duration_seconds": None,
        "minimum_coverage": None,
        "minimum_samples": None,
        "aggregation": None,
        "severity": "WARNING",
    },
}


def _seed_profile(bind, rule_code: str, sensor_model_code: str) -> None:
    rule_id = bind.scalar(sa.text("SELECT id FROM alert_rules WHERE code=:code"), {"code": rule_code})
    model_id = bind.scalar(sa.text("SELECT id FROM sensor_models WHERE code=:code"), {"code": sensor_model_code})
    if rule_id is None or model_id is None:
        return
    profile_code = f"{rule_code}_CANONICAL"
    profile_id = bind.scalar(
        sa.text(
            """
            INSERT INTO alert_rule_profiles (rule_id, code, name, config, is_enabled, created_at, updated_at)
            VALUES (:rule_id, :code, :name, CAST('{}' AS jsonb), true, now(), now())
            ON CONFLICT (code) DO UPDATE
            SET rule_id=EXCLUDED.rule_id, is_enabled=true, updated_at=now()
            RETURNING id
            """
        ),
        {"rule_id": rule_id, "code": profile_code, "name": f"Áp dụng cho SensorModel {sensor_model_code}"},
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO alert_rule_sensor_model_profiles (profile_id, sensor_model_id)
            VALUES (:profile_id, :model_id)
            ON CONFLICT DO NOTHING
            """
        ),
        {"profile_id": profile_id, "model_id": model_id},
    )


def upgrade() -> None:
    bind = op.get_bind()

    for code, config in INCOMPLETE_TYPED_CONFIGS.items():
        bind.execute(
            sa.text(
                """
                UPDATE alert_rule_revisions AS revision
                SET condition_schema_version=2, condition_config=CAST(:config AS jsonb), status='INCOMPLETE'
                FROM alert_rules AS rule
                WHERE revision.rule_id=rule.id AND rule.code=:code
                """
            ),
            {"code": code, "config": json.dumps(config)},
        )

    bind.execute(
        sa.text(
            """
            UPDATE alert_rule_revisions AS revision
            SET condition_schema_version=2,
                condition_config=revision.condition_config || CAST('{"max_running_current_a": null}' AS jsonb),
                status='INCOMPLETE'
            FROM alert_rules AS rule
            WHERE revision.rule_id=rule.id
              AND rule.evaluator_type IN ('ACTUATOR_FEEDBACK','SCHEDULE_FEEDBACK')
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE alert_rule_revisions AS revision
            SET status='PUBLISHED', published_at=COALESCE(published_at, now())
            FROM alert_rules AS rule
            WHERE revision.id=rule.current_revision_id AND rule.code = ANY(:codes)
            """
        ),
        {"codes": list(PUBLISHED_RULE_CODES)},
    )

    for rule_code, model_code in CANONICAL_SENSOR_PROFILES:
        _seed_profile(bind, rule_code, model_code)

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_published_alert_revision_content_update()
        RETURNS trigger AS $$
        BEGIN
            -- published_at is permanent history; RETIRED revisions must remain
            -- just as immutable as currently PUBLISHED revisions.
            IF OLD.published_at IS NOT NULL AND (
                NEW.rule_id IS DISTINCT FROM OLD.rule_id OR
                NEW.revision IS DISTINCT FROM OLD.revision OR
                NEW.business_risk_level IS DISTINCT FROM OLD.business_risk_level OR
                NEW.condition_schema_version IS DISTINCT FROM OLD.condition_schema_version OR
                NEW.condition_config IS DISTINCT FROM OLD.condition_config OR
                NEW.message_template IS DISTINCT FROM OLD.message_template OR
                NEW.consequence IS DISTINCT FROM OLD.consequence OR
                NEW.recommended_action IS DISTINCT FROM OLD.recommended_action
            ) THEN
                RAISE EXCEPTION 'Published alert rule revision content is immutable; create a new revision';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_alert_rule_revision_immutable ON alert_rule_revisions")
    op.execute(
        """
        CREATE TRIGGER trg_alert_rule_revision_immutable
        BEFORE UPDATE ON alert_rule_revisions
        FOR EACH ROW EXECUTE FUNCTION prevent_published_alert_revision_content_update()
        """
    )


def downgrade() -> None:
    raise RuntimeError(
        "0028 publishes validated business rules and protects revision history; "
        "restore from backup instead of downgrading destructively"
    )
