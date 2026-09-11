import re
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from app.core.enums import UserRole, UserStatus
from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.permission import Role
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User


@pytest.mark.asyncio
async def test_create_aquaponics_system_uses_generated_code_and_explicit_owner() -> None:
    suffix = uuid4().hex[:10]
    user_ids: list[int] = []
    system_ids: list[str] = []
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(User).where(User.system_role == UserRole.ADMIN))
        viewer_role = await db.scalar(select(Role).where(Role.code == "VIEWER"))
        assert admin and viewer_role
        active = User(username=f"owner-{suffix}", password_hash=hash_password("TestPassword@123"),
            full_name="Active owner", email=f"owner-{suffix}@example.test", phone_number=f"08{suffix[:8]}",
            address="", system_role=UserRole.VIEWER, role_id=viewer_role.id, status=UserStatus.ACTIVE,
            must_change_password=False)
        inactive = User(username=f"inactive-{suffix}", password_hash=hash_password("TestPassword@123"),
            full_name="Inactive owner", email=f"inactive-{suffix}@example.test", phone_number=f"07{suffix[:8]}",
            address="", system_role=UserRole.VIEWER, role_id=viewer_role.id, status=UserStatus.DISABLED,
            must_change_password=False)
        db.add_all([active, inactive]); await db.commit(); await db.refresh(active); await db.refresh(inactive)
        user_ids.extend([active.id, inactive.id])
        headers = {"Authorization": f"Bearer {create_access_token(str(admin.id), {'role': 'ADMIN', 'token_version': admin.token_version})}"}
        active_id, inactive_id, admin_id = str(active.public_id), str(inactive.public_id), str(admin.public_id)

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            created = []
            for _ in range(2):
                response = await client.post(f"/api/v1/users/{active_id}/aquaponics-systems",
                    headers=headers, json={"name": "Hệ thống cùng tên"})
                assert response.status_code == 201, response.text
                created.append(response.json())
                system_ids.append(response.json()["id"])
            assert created[0]["owner_user_id"] == active_id
            assert created[1]["owner_user_id"] == active_id
            assert created[0]["code"] != created[1]["code"]
            assert all(re.fullmatch(r"AQS-[A-Z0-9_-]{12}", item["code"]) for item in created)
            owned = await client.get(f"/api/v1/users/{active_id}/aquaponics-systems", headers=headers)
            assert owned.status_code == 200
            assert {item["id"] for item in owned.json()} == {item["id"] for item in created}
            assert all(item["relationship"] == "OWNER" for item in owned.json())

            extra_code = await client.post(f"/api/v1/users/{active_id}/aquaponics-systems",
                headers=headers, json={"name": "Không hợp lệ", "code": "CLIENT-CODE"})
            assert extra_code.status_code == 422
            missing_owner = await client.post("/api/v1/aquaponics-systems", headers=headers, json={"name": "Thiếu owner"})
            assert missing_owner.status_code == 422
            inactive_owner = await client.post("/api/v1/aquaponics-systems", headers=headers,
                json={"name": "Owner inactive", "owner_user_id": inactive_id})
            assert inactive_owner.status_code == 422
            missing_user = await client.post("/api/v1/aquaponics-systems", headers=headers,
                json={"name": "Owner missing", "owner_user_id": str(uuid4())})
            assert missing_user.status_code == 404
            inactive_user_path = await client.post(f"/api/v1/users/{inactive_id}/aquaponics-systems",
                headers=headers, json={"name": "Owner inactive path"})
            assert inactive_user_path.status_code == 422

            global_create = await client.post("/api/v1/aquaponics-systems", headers=headers,
                json={"name": "Explicit owner", "owner_user_id": active_id})
            assert global_create.status_code == 201, global_create.text
            system_ids.append(global_create.json()["id"])
            assert global_create.json()["owner_user_id"] == active_id
            assert global_create.json()["owner_user_id"] != admin_id
            patch_code = await client.patch(f"/api/v1/aquaponics-systems/{global_create.json()['id']}",
                headers=headers, json={"code": "CHANGED"})
            assert patch_code.status_code == 422

            async with AsyncSessionLocal() as db:
                internal_system_ids = select(Project.id).where(Project.public_id.in_(system_ids))
                assert await db.scalar(select(ProjectMember.id).where(
                    ProjectMember.project_id.in_(internal_system_ids), ProjectMember.role == "OWNER")) is None
    finally:
        async with AsyncSessionLocal() as db:
            internal_system_ids = select(Project.id).where(Project.public_id.in_(system_ids))
            await db.execute(delete(ProjectMember).where(ProjectMember.project_id.in_(internal_system_ids)))
            await db.execute(delete(Project).where(Project.public_id.in_(system_ids)))
            await db.execute(delete(User).where(User.id.in_(user_ids)))
            await db.commit()
