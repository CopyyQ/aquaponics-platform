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
from app.models.project import Project
from app.models.user import User


@pytest_asyncio.fixture(scope="session", autouse=True)
async def disposable_runtime_fixture():
    created_ids: dict[str, int] = {}
    async with AsyncSessionLocal() as db:
        owner = await db.scalar(
            select(User).where(User.username == "codex-test-owner")
        )
        if owner is None:
            owner = User(
                username="codex-test-owner",
                password_hash=hash_password("CodexTestOwner@123"),
                full_name="Chủ dự án kiểm thử",
                email="codex-test-owner@example.test",
                phone_number="0000000001",
                address="",
                system_role=UserRole.OWNER,
                status=UserStatus.ACTIVE,
                must_change_password=False,
            )
            db.add(owner)
            await db.flush()
            created_ids["owner"] = owner.id
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
        await db.execute(delete(Device).where(Device.id == created_ids["device"]))
        await db.execute(delete(Project).where(Project.id == created_ids["project"]))
        if "owner" in created_ids:
            await db.execute(delete(User).where(User.id == created_ids["owner"]))
        await db.commit()
    await engine.dispose()
