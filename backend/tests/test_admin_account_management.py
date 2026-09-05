from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal, engine
from app.core.enums import UserRole, UserStatus
from app.core.security import create_access_token, hash_password, verify_password
from app.main import app
from app.models.audit import AuditLog
from app.models.user import User


def auth_header(user: User) -> dict[str, str]:
    token = create_access_token(
        str(user.id),
        {"role": user.system_role.value, "token_version": user.token_version},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_create_and_securely_set_user_password() -> None:
    suffix = str(uuid4().int)[-10:]
    created_user_id: int | None = None
    attacker_id: int | None = None
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(
            select(User).where(
                User.system_role == UserRole.ADMIN,
                User.status == UserStatus.ACTIVE,
                User.is_deleted.is_(False),
            )
        )
        if admin is None:
            pytest.skip("Cần seed Admin active để chạy integration test")
        attacker = User(
            username=f"owner-{suffix}",
            password_hash=hash_password("OwnerPass@123"),
            full_name="Owner kiểm thử",
            email=f"owner-{suffix}@example.com",
            phone_number=f"08{suffix[:8]}",
            address="Cần Thơ",
            system_role=UserRole.OWNER,
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        db.add(attacker)
        await db.commit()
        await db.refresh(attacker)
        attacker_id = attacker.id
        admin_headers = auth_header(admin)
        owner_headers = auth_header(attacker)

    payload = {
        "username": f"account-{suffix}",
        "full_name": "  Nguyễn Văn Kiểm Thử  ",
        "email": f"  ACCOUNT-{suffix}@EXAMPLE.COM  ",
        "phone_number": f"09{suffix[:8]}",
        "address": "  Cần Thơ  ",
        "system_role": "OWNER",
        "status": "ACTIVE",
        "password": "OldPassword@123",
        "confirm_password": "OldPassword@123",
        "must_change_password": True,
    }
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            forbidden = await client.post("/api/v1/admin/users", headers=owner_headers, json=payload)
            assert forbidden.status_code == 403

            missing_phone = payload | {"username": f"missing-{suffix}"}
            missing_phone.pop("phone_number")
            assert (await client.post("/api/v1/admin/users", headers=admin_headers, json=missing_phone)).status_code == 422

            mismatch = payload | {"username": f"mismatch-{suffix}", "confirm_password": "Different@123"}
            assert (await client.post("/api/v1/admin/users", headers=admin_headers, json=mismatch)).status_code == 422

            created = await client.post("/api/v1/admin/users", headers=admin_headers, json=payload)
            assert created.status_code == 201, created.text
            body = created.json()
            created_user_id = body["id"]
            assert body["full_name"] == "Nguyễn Văn Kiểm Thử"
            assert body["email"] == f"account-{suffix}@example.com"
            assert body["must_change_password"] is True
            assert "password_hash" not in body

            duplicate_username = payload | {"email": f"other-{suffix}@example.com", "phone_number": f"07{suffix[:8]}"}
            assert (await client.post("/api/v1/admin/users", headers=admin_headers, json=duplicate_username)).status_code == 409
            duplicate_email = payload | {"username": f"other-{suffix}", "phone_number": f"06{suffix[:8]}"}
            assert (await client.post("/api/v1/admin/users", headers=admin_headers, json=duplicate_email)).status_code == 409
            duplicate_phone = payload | {"username": f"phone-{suffix}", "email": f"phone-{suffix}@example.com"}
            assert (await client.post("/api/v1/admin/users", headers=admin_headers, json=duplicate_phone)).status_code == 409

            old_token = create_access_token(str(created_user_id), {"role": "OWNER", "token_version": 0})
            denied_reset = await client.post(
                f"/api/v1/admin/users/{created_user_id}/set-password",
                headers=owner_headers,
                json={"new_password": "NewPassword@123", "confirm_password": "NewPassword@123"},
            )
            assert denied_reset.status_code == 403

            reset = await client.post(
                f"/api/v1/admin/users/{created_user_id}/set-password",
                headers=admin_headers,
                json={
                    "new_password": "NewPassword@123",
                    "confirm_password": "NewPassword@123",
                    "invalidate_sessions": True,
                    "must_change_password": False,
                },
            )
            assert reset.status_code == 200, reset.text
            assert reset.json() == {
                "success": True,
                "message": "Đã cập nhật mật khẩu.",
                "sessions_invalidated": True,
                "must_change_password": False,
            }
            revoked = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
            assert revoked.status_code == 401
            assert revoked.json()["code"] == "TOKEN_REVOKED"
            assert (await client.post("/api/v1/auth/login", json={"username": payload["username"], "password": "OldPassword@123"})).status_code == 401
            assert (await client.post("/api/v1/auth/login", json={"username": payload["username"], "password": "NewPassword@123"})).status_code == 200
            activity = await client.get(f"/api/v1/admin/users/{created_user_id}/activity", headers=admin_headers)
            assert activity.status_code == 200
            assert any(item["action"] == "ADMIN_SET_USER_PASSWORD" and "Nguyễn Văn Kiểm Thử" in item["target_name"] for item in activity.json())

            assert (await client.post(f"/api/v1/admin/users/{created_user_id}/disable", headers=admin_headers)).status_code == 200
            assert (await client.post(
                f"/api/v1/admin/users/{created_user_id}/set-password",
                headers=admin_headers,
                json={"new_password": "DisabledPass@123", "confirm_password": "DisabledPass@123", "invalidate_sessions": False},
            )).status_code == 200

            assert (await client.delete(f"/api/v1/admin/users/{created_user_id}", headers=admin_headers)).status_code == 200
            deleted_reset = await client.post(
                f"/api/v1/admin/users/{created_user_id}/set-password",
                headers=admin_headers,
                json={"new_password": "DeletedPass@123", "confirm_password": "DeletedPass@123"},
            )
            assert deleted_reset.status_code == 409

        async with AsyncSessionLocal() as db:
            stored = await db.get(User, created_user_id)
            assert stored is not None
            assert stored.status == UserStatus.SOFT_DELETED
            assert stored.token_version == 3
            assert verify_password("DisabledPass@123", stored.password_hash)
            assert stored.password_hash not in {"OldPassword@123", "NewPassword@123", "DisabledPass@123"}
            password_logs = list((await db.scalars(select(AuditLog).where(AuditLog.entity_type == "USER", AuditLog.entity_id == created_user_id))).all())
            assert {log.action for log in password_logs} >= {"CREATE_USER", "ADMIN_SET_USER_PASSWORD"}
            serialized = " ".join(str(log.new_data) + str(log.old_data) for log in password_logs)
            for secret in ("OldPassword@123", "NewPassword@123", "DisabledPass@123"):
                assert secret not in serialized
    finally:
        async with AsyncSessionLocal() as db:
            ids = [item for item in (created_user_id, attacker_id) if item is not None]
            if ids:
                await db.execute(delete(AuditLog).where((AuditLog.user_id.in_(ids)) | ((AuditLog.entity_type == "USER") & (AuditLog.entity_id.in_(ids)))))
                await db.execute(delete(User).where(User.id.in_(ids)))
                await db.commit()
        await engine.dispose()
