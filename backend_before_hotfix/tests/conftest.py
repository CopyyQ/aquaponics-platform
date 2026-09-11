import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/aquaponics_codex_test_default",
)
test_database_name = os.environ["DATABASE_URL"].rsplit("/", maxsplit=1)[-1].split("?", maxsplit=1)[0]
if not test_database_name.startswith(("aquaponics_codex_", "aquaponics_test_")):
    raise RuntimeError(
        "Backend tests require an explicitly disposable aquaponics_codex_* database; "
        f"got {test_database_name!r}"
    )
os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-123456789")
os.environ.setdefault("FERNET_KEY", "ulEXv2cI-PsZu2SBChJNe9tKYU19H9ElRuQO9nZTqpk=")
os.environ.setdefault("DEFAULT_ADMIN_PASSWORD", "test-only-admin-password")
os.environ.setdefault("PYTEST_RUNNING", "1")

import pytest_asyncio
from sqlalchemy import delete, select

from app.core.enums import DeviceStatus, ProjectStatus, UserRole, UserStatus
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.device import Device
from app.models.sensor import Sensor
from app.models.actuator import Actuator
from app.models.telemetry import TelemetryReading
from app.models.alert import SensorAlert
from app.models.operational_alert import NotificationDelivery, NotificationOutbox, OperationalIncident
from app.models.project import Project
from app.models.user import User
from app.models.permission import Role
from scripts.seed import seed


@pytest_asyncio.fixture(scope="session", autouse=True)
async def disposable_runtime_fixture():
    created_ids: dict[str, int] = {}
    # Match the application bootstrap rather than making ad-hoc catalog rows
    # in individual tests. The production seed is idempotent.
    await seed()
    async with AsyncSessionLocal() as db:
        roles = {row.code: row.id for row in (await db.scalars(select(Role))).all()}
        owner = await db.scalar(
            select(User).where(User.username == "codex-test-owner")
        )
        if owner is None:
            owner = User(
                username="codex-test-owner",
                password_hash=hash_password("CodexTestOwner@123"),
                full_name="Chủ dự án kiểm thử",
                email="codex-test-owner@example.test",
                phone_number="0000000002",
                address="",
                system_role=UserRole.OWNER,
                status=UserStatus.ACTIVE,
                must_change_password=False,
                role_id=roles["OWNER"],
            )
            db.add(owner)
            await db.flush()
            created_ids["owner"] = owner.id
        viewer = await db.scalar(select(User).where(User.username == "codex-test-viewer"))
        if viewer is None:
            viewer = User(username="codex-test-viewer", password_hash=hash_password("CodexTestViewer@123"),
                full_name="Người xem kiểm thử", email="codex-test-viewer@example.test", phone_number="0000000003",
                address="", system_role=UserRole.VIEWER, role_id=roles["VIEWER"], status=UserStatus.ACTIVE,
                must_change_password=False)
            db.add(viewer); await db.flush(); created_ids["viewer"] = viewer.id
        # A prior interrupted run may have skipped fixture teardown. Remove
        # only this fixture's deterministic disposable rows before recreating
        # them, keeping repeated local/full-suite runs idempotent.
        stale_project = await db.scalar(
            select(Project).where(Project.code == "CODEX-TEST-RUNTIME")
        )
        if stale_project is not None:
            stale_devices = select(Device.id).where(Device.project_id == stale_project.id)
            stale_sensors = select(Sensor.id).where(Sensor.device_id.in_(stale_devices))
            stale_incidents = select(OperationalIncident.id).where(OperationalIncident.project_id == stale_project.id)
            await db.execute(delete(NotificationDelivery).where(NotificationDelivery.incident_id.in_(stale_incidents)))
            await db.execute(delete(NotificationOutbox).where(NotificationOutbox.project_id == stale_project.id))
            await db.execute(delete(OperationalIncident).where(OperationalIncident.project_id == stale_project.id))
            await db.execute(delete(TelemetryReading).where(TelemetryReading.sensor_id.in_(stale_sensors)))
            await db.execute(delete(SensorAlert).where(SensorAlert.sensor_id.in_(stale_sensors)))
            await db.execute(delete(Sensor).where(Sensor.device_id.in_(stale_devices)))
            await db.execute(delete(Actuator).where(Actuator.device_id.in_(stale_devices)))
            await db.execute(delete(Device).where(Device.project_id == stale_project.id))
            await db.execute(delete(Project).where(Project.id == stale_project.id))
            await db.flush()
        project = Project(
            owner_user_id=owner.id,
            code="CODEX-TEST-RUNTIME",
            name="Dự án runtime kiểm thử",
            status=ProjectStatus.ACTIVE,
        )
        db.add(project)
        await db.flush()
        device = Device(
            project_id=project.id,
            code="CODEX-TEST-DEVICE",
            name="Thiết bị runtime kiểm thử",
            status=DeviceStatus.ONLINE,
            is_enabled=True,
        )
        db.add(device)
        await db.commit()
        created_ids["project"] = project.id
        created_ids["device"] = device.id

    yield

    async with AsyncSessionLocal() as db:
        device_sensors = select(Sensor.id).where(Sensor.device_id == created_ids["device"])
        runtime_incidents = select(OperationalIncident.id).where(OperationalIncident.project_id == created_ids["project"])
        await db.execute(delete(NotificationDelivery).where(NotificationDelivery.incident_id.in_(runtime_incidents)))
        await db.execute(delete(NotificationOutbox).where(NotificationOutbox.project_id == created_ids["project"]))
        await db.execute(delete(OperationalIncident).where(OperationalIncident.project_id == created_ids["project"]))
        await db.execute(delete(TelemetryReading).where(TelemetryReading.sensor_id.in_(device_sensors)))
        await db.execute(delete(SensorAlert).where(SensorAlert.sensor_id.in_(device_sensors)))
        await db.execute(delete(Sensor).where(Sensor.device_id == created_ids["device"]))
        await db.execute(delete(Actuator).where(Actuator.device_id == created_ids["device"]))
        await db.execute(delete(Device).where(Device.id == created_ids["device"]))
        await db.execute(delete(Project).where(Project.id == created_ids["project"]))
        if "owner" in created_ids:
            await db.execute(delete(User).where(User.id == created_ids["owner"]))
        if "viewer" in created_ids:
            await db.execute(delete(User).where(User.id == created_ids["viewer"]))
        await db.commit()
    await engine.dispose()
