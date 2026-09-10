import httpx
import pytest
from sqlalchemy import delete, select

from app.core.enums import UserRole
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.permission import Permission, RolePermission
from app.models.user import User
from app.services.permission_service import get_effective_permissions


@pytest.mark.asyncio
async def test_session_exposes_database_backed_effective_permissions() -> None:
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(User).where(User.system_role == UserRole.ADMIN))
        assert admin and admin.role_id
        token = create_access_token(str(admin.id), {"role": "ADMIN", "token_version": admin.token_version})
        expected = await get_effective_permissions(db, admin)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert set(response.json()["permissions"]) == expected
    assert "devices.update" in expected


@pytest.mark.asyncio
async def test_permission_assignment_is_revocable_without_changing_jwt() -> None:
    async with AsyncSessionLocal() as db:
        viewer = await db.scalar(select(User).where(User.system_role == UserRole.VIEWER))
        permission = await db.scalar(select(Permission).where(Permission.code == "devices.update"))
        assert viewer and permission and viewer.role_id
        assignment = await db.scalar(select(RolePermission).where(RolePermission.role_id == viewer.role_id, RolePermission.permission_id == permission.id))
        created = assignment is None
        if created:
            db.add(RolePermission(role_id=viewer.role_id, permission_id=permission.id))
            await db.commit()
        assert "devices.update" in await get_effective_permissions(db, viewer)
        if created:
            await db.execute(delete(RolePermission).where(RolePermission.role_id == viewer.role_id, RolePermission.permission_id == permission.id))
            await db.commit()
        assert "devices.update" not in await get_effective_permissions(db, viewer)
