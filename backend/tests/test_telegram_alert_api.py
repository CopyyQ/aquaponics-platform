from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from app.core.enums import UserRole
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.device import Device
from app.models.operational_alert import OperationalIncident
from app.models.project import Project
from app.models.project_settings import ProjectNotificationRecipient
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.telemetry import TelemetryReading
from app.models.threshold_alert_config import ThresholdAlertConfig
from app.models.user import User


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(
        str(user.id),
        {"role": user.system_role.value, "token_version": user.token_version},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_threshold_patch_api_re_evaluates_latest_reading_and_returns_canonical_config() -> None:
    suffix = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        project = await db.scalar(select(Project).where(Project.code == "CODEX-TEST-RUNTIME"))
        assert project is not None
        device = await db.scalar(select(Device).where(Device.project_id == project.id))
        owner = await db.get(User, project.owner_user_id)
        model = await db.scalar(select(SensorModel).where(SensorModel.code == "PH"))
        assert device is not None and owner is not None and model is not None
        sensor = Sensor(
            device_id=device.id,
            sensor_model_id=model.id,
            code=f"PH-API-{suffix}",
            name="Sensor pH API",
            is_enabled=True,
        )
        db.add(sensor)
        await db.flush()
        config = ThresholdAlertConfig(
            sensor_id=sensor.id,
            metric_type="SENSOR_VALUE",
            enabled=True,
            lower_threshold=6.0,
            upper_threshold=14.0,
            below_risk_level="LOW",
            above_risk_level="HIGH",
            delay_seconds=0,
        )
        db.add_all([
            config,
                TelemetryReading(
                    sensor_id=sensor.id,
                    value=10.8,
                    recorded_at=datetime.now(UTC),
                received_at=datetime.now(UTC),
            ),
        ])
        await db.commit()
        system_id, device_id, sensor_id = project.public_id, device.public_id, sensor.public_id
        sensor_internal_id = sensor.id
        headers = _headers(owner)

    url = f"/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors/{sensor_id}/threshold-alert"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        update = {
            "enabled": True,
            "lower_threshold": 7,
            "upper_threshold": 9,
            "below_risk_level": "LOW_MEDIUM",
            "above_risk_level": "VERY_HIGH",
            "below_message": "  Nội dung dưới do user nhập  ",
            "above_message": "Nội dung trên do user nhập",
            "below_consequence": "Ảnh hưởng dưới do user nhập",
            "above_consequence": "Ảnh hưởng trên do user nhập",
            "below_recommended_actions": "Khuyến nghị dưới do user nhập",
            "above_recommended_actions": "Khuyến nghị trên do user nhập",
            "delay_seconds": 10,
        }
        response = await client.patch(url, headers=headers, json=update)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["lower_threshold"] == 7
        assert body["upper_threshold"] == 9
        assert body["below_risk_level"] == "LOW_MEDIUM"
        assert body["above_risk_level"] == "VERY_HIGH"
        assert body["below_message"] == "Nội dung dưới do user nhập"
        for field in (
            "above_message", "below_consequence", "above_consequence",
            "below_recommended_actions", "above_recommended_actions",
        ):
            assert body[field] == update[field]
        assert body["delay_seconds"] == 10
        fetched = await client.get(url, headers=headers)
        assert fetched.status_code == 200
        assert fetched.json() == body
        invalid = await client.patch(url, headers=headers, json={"lower_threshold": 9, "upper_threshold": 9})
        assert invalid.status_code == 422

    async with AsyncSessionLocal() as db:
        incident = await db.scalar(select(OperationalIncident).where(
            OperationalIncident.sensor_id == sensor_internal_id,
            OperationalIncident.status == "PENDING",
        ))
        assert incident is not None
        assert incident.trigger_snapshot["value"] == 10.8
        assert incident.trigger_snapshot["threshold"] == 9
        assert incident.trigger_snapshot["threshold_direction"] == "ABOVE"
        assert incident.trigger_snapshot["message"] == "Nội dung trên do user nhập"
        assert incident.trigger_snapshot["consequence"] == "Ảnh hưởng trên do user nhập"
        assert incident.trigger_snapshot["recommended_actions"] == "Khuyến nghị trên do user nhập"
        assert incident.business_risk_level_snapshot == "VERY_HIGH"
        incident.status = "NORMALIZED"
        incident.normalized_at = datetime.now(UTC)
        await db.commit()


@pytest.mark.asyncio
async def test_notification_alert_and_history_endpoints_are_system_isolated() -> None:
    suffix = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        owner = await db.scalar(select(User).where(User.username == "codex-test-owner"))
        admin = await db.scalar(select(User).where(User.system_role == UserRole.ADMIN))
        assert owner is not None and admin is not None
        foreign_system = Project(
            owner_user_id=admin.id,
            code=f"FOREIGN-{suffix}",
            name="Foreign system",
            status="ACTIVE",
        )
        db.add(foreign_system)
        await db.flush()
        recipient = ProjectNotificationRecipient(
            project_id=foreign_system.id,
            name="Foreign recipient",
            telegram_chat_id="333333333",
            enabled=True,
        )
        db.add(recipient)
        await db.commit()
        foreign_system_id = foreign_system.id
        headers = _headers(owner)

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for path in (
                f"/api/v1/aquaponics-systems/{foreign_system_id}/alert-delivery/recipients",
                f"/api/v1/aquaponics-systems/{foreign_system_id}/alert-delivery/history",
                f"/api/v1/aquaponics-systems/{foreign_system_id}/alerts",
            ):
                response = await client.get(path, headers=headers)
                assert response.status_code in {403, 404}, (path, response.text)
            threshold_update = await client.patch(
                f"/api/v1/aquaponics-systems/{foreign_system_id}/devices/1/sensors/1/threshold-alert",
                headers=headers,
                json={"above_consequence": "Không được phép lưu"},
            )
            assert threshold_update.status_code in {403, 404}
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(ProjectNotificationRecipient).where(
                ProjectNotificationRecipient.project_id == foreign_system_id,
            ))
            await db.execute(delete(Project).where(Project.id == foreign_system_id))
            await db.commit()
