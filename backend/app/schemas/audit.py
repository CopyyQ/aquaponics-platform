from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    action: str
    entity_type: str
    entity_id: int | None
    description: str | None
    old_data: dict[str, Any] | None
    new_data: dict[str, Any] | None
    created_at: datetime
    actor: "AuditParty"
    target: "AuditTarget"


class AuditParty(BaseModel):
    id: int
    full_name: str
    username: str


class AuditTarget(BaseModel):
    id: int | None
    type: str
    display_name: str
