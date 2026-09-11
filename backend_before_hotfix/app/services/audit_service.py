from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "temporary_password",
    "confirm_password",
    "current_password",
    "new_password",
    "verification_secret",
    "secret_encrypted",
    "token",
    "signature",
    "secret_key",
    "api_key",
    "cookie",
    "session",
    "telegram_bot_token",
    "telegram_chat_id",
    "mqtt_password",
    "database_password",
}


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize_value(item)
            for key, item in value.items()
            if key.lower() not in SENSITIVE_KEYS
            and not any(fragment in key.lower() for fragment in ("password", "token", "secret", "credential", "cookie", "session"))
        }
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


def sanitize(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    return _sanitize_value(data)


async def write_audit(
    db: AsyncSession,
    *,
    user_id: int,
    project_id: int | None = None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    description: str | None = None,
    old_data: dict[str, Any] | None = None,
    new_data: dict[str, Any] | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        project_id=project_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        old_data=sanitize(old_data),
        new_data=sanitize(new_data),
        created_at=datetime.now(UTC),
    )
    db.add(log)
    await db.flush()
    return log
