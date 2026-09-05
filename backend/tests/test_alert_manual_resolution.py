from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import delete, func, select
from test_visibility_authorization import auth_header, visibility_data  # noqa: F401

from app.core.enums import AlertStatus, AlertType
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.alert import SensorAlert
from app.models.audit import AuditLog
from app.models.sensor import Sensor
from app.services.alert_service import evaluate_threshold
from app.services.project_notification_service import format_alert_message


def test_confirmed_resolution_telegram_wording_actor_note_and_local_time() -> None:
    from types import SimpleNamespace

    alert = SimpleNamespace(
        severity="WARNING",
        message="Cảm biến pH vượt ngưỡng trên 8.5",
        trigger_value=8.6,
        started_at=datetime(2026, 8, 17, 3, 59, 30, tzinfo=UTC),
        resolved_at=datetime(2026, 8, 17, 4, 20, 0, tzinfo=UTC),
        resolved_by_user=SimpleNamespace(full_name="Nguyễn Văn A"),
        resolved_by_user_id=7,
        resolution_note="Đã kiểm tra hệ thống và điều chỉnh nước.",
    )
    message = format_alert_message(
        transition="RESOLVED_CONFIRMED",
        project_name="Dự án nuôi cá trê",
        alert=alert,
        sensor_name="Cảm biến pH",
        device_name="Thiết bị đo nước",
    )
    assert message.splitlines()[0] == "✅ CẢNH BÁO ĐÃ ĐƯỢC XÁC NHẬN KHẮC PHỤC"
    assert "Xác nhận bởi: Nguyễn Văn A" in message
    assert "Ghi chú: Đã kiểm tra hệ thống và điều chỉnh nước." in message
    assert "17/08/2026 11:20:00 (Asia/Ho_Chi_Minh)" in message


@pytest.mark.asyncio
async def test_flapping_reuses_one_unresolved_incident_without_auto_resolution(visibility_data) -> None:
    data = visibility_data
    async with AsyncSessionLocal() as db:
        sensor = await db.get(Sensor, data["active_sensor"])
        assert sensor is not None
        sensor.warning_enabled = True
        sensor.lower_threshold = 6.0
        sensor.upper_threshold = 8.5
        sensor.alert_delay_seconds = 0
        started = datetime.now(UTC)
        transitions: list[str] = []
        for offset, value in enumerate((8.6, 8.3, 8.7, 8.4, 8.8)):
            transitions.extend(
                transition
                for _, transition in await evaluate_threshold(
                    db, sensor, value, started + timedelta(seconds=offset)
                )
            )
        await db.flush()
        alerts = list((await db.scalars(select(SensorAlert).where(
            SensorAlert.sensor_id == sensor.id,
            SensorAlert.alert_type == AlertType.ABOVE_UPPER_THRESHOLD,
        ))).all())
        assert len(alerts) == 1
        assert alerts[0].status == AlertStatus.OPEN
        assert alerts[0].condition_active is True
        assert alerts[0].resolved_at is None
        assert alerts[0].resolved_by_user_id is None
        assert transitions == ["OPENED", "ABNORMAL_READING", "ABNORMAL_READING"]
        assert alerts[0].occurrence_count == 3
        assert alerts[0].trigger_value == 8.8
        await db.rollback()


@pytest.mark.asyncio
async def test_manual_resolution_requires_normal_condition_and_records_actor_note_activity(
    visibility_data, monkeypatch
) -> None:
    data = visibility_data
    dispatched: list[tuple[int, str]] = []

    async def capture_dispatch(_db, *, alert_id: int, transition: str) -> None:
        dispatched.append((alert_id, transition))

    monkeypatch.setattr("app.services.alert_service.dispatch_alert_transition", capture_dispatch)
    async with AsyncSessionLocal() as db:
        sensor = await db.get(Sensor, data["active_sensor"])
        assert sensor is not None
        sensor.warning_enabled = True
        sensor.upper_threshold = 8.5
        sensor.alert_delay_seconds = 0
        first = await evaluate_threshold(db, sensor, 8.6, datetime.now(UTC))
        alert = first[0][0]
        await db.commit()
        alert_id = alert.id

    headers = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        blocked = await client.post(
            f"/api/v1/alerts/{alert_id}/resolve",
            headers=headers,
            json={"resolution_note": "Đã kiểm tra nhưng giá trị vẫn cao"},
        )
        assert blocked.status_code == 409

    async with AsyncSessionLocal() as db:
        sensor = await db.get(Sensor, data["active_sensor"])
        assert sensor is not None
        await evaluate_threshold(db, sensor, 8.3, datetime.now(UTC))
        await db.commit()

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resolved = await client.post(
            f"/api/v1/alerts/{alert_id}/resolve",
            headers=headers,
            json={"resolution_note": "Đã kiểm tra hệ thống và điều chỉnh nước."},
        )
        assert resolved.status_code == 200
        payload = resolved.json()
        assert payload["status"] == "RESOLVED"
        assert payload["condition_active"] is False
        assert payload["resolved_by_user_id"] == data["admin_id"]
        assert payload["resolved_at"] is not None
        assert payload["resolution_note"] == "Đã kiểm tra hệ thống và điều chỉnh nước."

    async with AsyncSessionLocal() as db:
        activity = await db.scalar(select(AuditLog).where(
            AuditLog.project_id == data["active_project"],
            AuditLog.action == "ALERT_RESOLVED",
            AuditLog.entity_id == alert_id,
        ))
        assert activity is not None
        assert activity.user_id == data["admin_id"]
        assert dispatched == [(alert_id, "RESOLVED_CONFIRMED")]

        sensor = await db.get(Sensor, data["active_sensor"])
        assert sensor is not None
        new_transitions = await evaluate_threshold(db, sensor, 8.7, datetime.now(UTC))
        await db.flush()
        assert [transition for _, transition in new_transitions] == ["OPENED"]
        assert new_transitions[0][0].id != alert_id
        assert await db.scalar(select(func.count(SensorAlert.id)).where(
            SensorAlert.sensor_id == sensor.id,
            SensorAlert.alert_type == AlertType.ABOVE_UPPER_THRESHOLD,
        )) == 2
        await db.execute(delete(AuditLog).where(AuditLog.entity_type == "ALERT", AuditLog.entity_id.in_([alert_id, new_transitions[0][0].id])))
        await db.execute(delete(SensorAlert).where(SensorAlert.id.in_([alert_id, new_transitions[0][0].id])))
        await db.commit()
