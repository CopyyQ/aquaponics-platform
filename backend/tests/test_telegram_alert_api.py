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
        system_id, device_id, sensor_id = project.id, device.id, sensor.id
        headers = _headers(owner)

    url = f"/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors/{sensor_id}/threshold-alert"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(url, headers=headers, json={"upper_threshold": 7.5, "above_risk_level": None})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["upper_threshold"] == 7.5
        assert body["above_risk_level"] == "HIGH"
        fetched = await client.get(url, headers=headers)
        assert fetched.status_code == 200
        assert fetched.json() == body

    async with AsyncSessionLocal() as db:
        incident = await db.scalar(select(OperationalIncident).where(
            OperationalIncident.sensor_id == sensor_id,
            OperationalIncident.status == "OPEN",
        ))
        assert incident is not None
        assert incident.trigger_snapshot["value"] == 10.8
        assert incident.trigger_snapshot["threshold"] == 7.5
        assert incident.trigger_snapshot["threshold_direction"] == "ABOVE"
        assert incident.business_risk_level_snapshot == "HIGH"
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
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(ProjectNotificationRecipient).where(
                ProjectNotificationRecipient.project_id == foreign_system_id,
            ))
            await db.execute(delete(Project).where(Project.id == foreign_system_id))
            await db.commit()
