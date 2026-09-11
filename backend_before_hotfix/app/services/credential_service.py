import io
import json
import zipfile
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_secret, generate_device_secret
from app.models.device import Device, DeviceCredential
from app.models.sensor import Sensor, SensorModel
from app.models.user import User
from app.services.audit_service import write_audit


async def get_active_credential(db: AsyncSession, device_id: int) -> DeviceCredential | None:
    return await db.scalar(
        select(DeviceCredential)
        .where(DeviceCredential.device_id == device_id, DeviceCredential.revoked_at.is_(None))
        .order_by(DeviceCredential.version.desc())
    )


async def issue_credential(
    db: AsyncSession,
    device: Device,
    actor: User,
    expires_at: datetime | None = None,
    *,
    revoke_existing: bool = False,
) -> tuple[DeviceCredential, str]:
    active = await get_active_credential(db, device.id)
    now = datetime.now(UTC)
    if active and not revoke_existing:
        raise HTTPException(status_code=409, detail="Thiết bị đã có credential đang hoạt động")
    if active:
        active.revoked_at = now

    max_version = await db.scalar(
        select(func.coalesce(func.max(DeviceCredential.version), 0)).where(
            DeviceCredential.device_id == device.id
        )
    )
    secret = generate_device_secret()
    credential = DeviceCredential(
        device_id=device.id,
        version=int(max_version or 0) + 1,
        secret_encrypted=encrypt_secret(secret),
        issued_at=now,
        expires_at=expires_at,
        last_used_at=None,
        revoked_at=None,
        created_by=actor.id,
        created_at=now,
    )
    db.add(credential)
    await db.flush()
    await write_audit(
        db,
        user_id=actor.id,
        action="ROTATE_DEVICE_CREDENTIAL" if active else "ISSUE_DEVICE_CREDENTIAL",
        entity_type="DEVICE_CREDENTIAL",
        entity_id=credential.id,
        new_data={
            "device_id": device.id,
            "version": credential.version,
            "expires_at": expires_at.isoformat() if expires_at else None,
        },
    )
    await db.commit()
    await db.refresh(credential)
    return credential, secret


async def revoke_credential(db: AsyncSession, device: Device, actor: User) -> None:
    active = await get_active_credential(db, device.id)
    if not active:
        raise HTTPException(status_code=404, detail="Không có credential đang hoạt động")
    active.revoked_at = datetime.now(UTC)
    await write_audit(
        db,
        user_id=actor.id,
        action="REVOKE_DEVICE_CREDENTIAL",
        entity_type="DEVICE_CREDENTIAL",
        entity_id=active.id,
        new_data={"device_id": device.id, "version": active.version},
    )
    await db.commit()


async def build_connection_package(
    *,
    db: AsyncSession,
    device: Device,
    credential: DeviceCredential,
    secret: str,
    server_url: str,
) -> bytes:
    sensor_rows = (
        await db.execute(
            select(Sensor, SensorModel)
            .join(SensorModel, Sensor.sensor_model_id == SensorModel.id)
            .where(
                Sensor.device_id == device.id,
                Sensor.is_deleted.is_(False),
                Sensor.is_enabled.is_(True),
            )
            .order_by(Sensor.name)
        )
    ).all()
    sensors = [
        {
            "sensor_code": sensor.code,
            "model_code": model.code,
            "name": sensor.name,
            "unit": model.unit,
        }
        for sensor, model in sensor_rows
    ]
    config = {
        "device": {
            "code": device.code,
            "name": device.name,
            "project_id": device.project_id,
        },
        "credential": {
            "version": credential.version,
            "verification_secret": secret,
            "algorithm": "HMAC-SHA256",
            "expires_at": credential.expires_at.isoformat() if credential.expires_at else None,
        },
        "server": {
            "base_url": server_url.rstrip("/"),
            "telemetry_endpoint": "/device-api/v1/telemetry",
        },
        "sensors": sensors,
    }
    sensor_lines = "\n".join(
        f"- `{item['sensor_code']}` — {item['name']} ({item['model_code']}, {item['unit']})"
        for item in sensors
    ) or "- Thiết bị chưa có cảm biến active."
    sample_readings = ",\n".join(
        f'    {{"sensor_code": "{item["sensor_code"]}", "value": 0}}'
        for item in sensors
    )
    guide = f"""# Hướng dẫn kết nối thiết bị {device.name}

## Thông tin kết nối

- Mã thiết bị: `{device.code}`
- Phiên bản credential: `{credential.version}`
- Server: `{server_url.rstrip('/')}`
- Endpoint: `/device-api/v1/telemetry`
- Thuật toán: `HMAC-SHA256`

> Mã xác minh chỉ xuất hiện một lần trong gói vừa tạo. Nếu mất gói, hãy rotate credential.

## Header bắt buộc

```http
X-Device-Code: {device.code}
X-Credential-Version: {credential.version}
X-Timestamp: <UNIX_TIMESTAMP>
X-Signature: <BASE64_HMAC_SHA256>
Content-Type: application/json
```

Dữ liệu ký là: `timestamp + \".\" + raw_request_body`.

## Cảm biến active ({len(sensors)})

{sensor_lines}

## Payload mẫu

```json
{{
  "sent_at": "2026-07-21T12:00:00Z",
  "readings": [
{sample_readings}
  ]
}}
```

> Mã xác minh nằm trong `device-config.json`. Đây là bí mật tương đương mật khẩu. Không đưa lên Git hoặc chia sẻ công khai.
> Khi thêm Sensor mới, hãy tải lại gói nếu firmware cần cấu hình danh sách Sensor.
"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("device-config.json", json.dumps(config, ensure_ascii=False, indent=2))
        archive.writestr("connection-guide.md", guide)
    return buffer.getvalue()
