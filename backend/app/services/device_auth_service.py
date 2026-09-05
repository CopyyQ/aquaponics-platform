from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import DeviceStatus
from app.core.security import decrypt_secret, verify_hmac_signature
from app.models.device import Device, DeviceCredential


async def authenticate_device_request(
    db: AsyncSession,
    *,
    device_code: str,
    credential_version: int,
    timestamp: str,
    signature: str,
    raw_body: bytes,
) -> tuple[Device, DeviceCredential]:
    try:
        request_time = datetime.fromtimestamp(int(timestamp), tz=UTC)
    except (TypeError, ValueError, OSError):
        raise HTTPException(status_code=401, detail="Timestamp không hợp lệ")

    age = abs((datetime.now(UTC) - request_time).total_seconds())
    if age > settings.device_signature_max_age_seconds:
        raise HTTPException(status_code=401, detail="Request đã quá hạn")

    device = await db.scalar(
        select(Device).where(Device.code == device_code, Device.is_deleted.is_(False))
    )
    if device is None or device.status == DeviceStatus.DISABLED:
        raise HTTPException(status_code=401, detail="Thiết bị không hợp lệ")

    credential = await db.scalar(
        select(DeviceCredential).where(
            DeviceCredential.device_id == device.id,
            DeviceCredential.version == credential_version,
            DeviceCredential.revoked_at.is_(None),
        )
    )
    if credential is None:
        raise HTTPException(status_code=401, detail="Credential không hợp lệ")
    if credential.expires_at and credential.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Credential đã hết hạn")

    secret = decrypt_secret(credential.secret_encrypted)
    if not verify_hmac_signature(secret, timestamp, raw_body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chữ ký thiết bị không hợp lệ",
        )
    return device, credential
