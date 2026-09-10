from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AquaponicsSystemActivityActor(BaseModel):
    id: UUID
    name: str


class AquaponicsSystemActivityEntity(BaseModel):
    type: str
    id: UUID | int | None
    name: str


class AquaponicsSystemActivityRead(BaseModel):
    id: int
    action: str
    actor: AquaponicsSystemActivityActor
    entity: AquaponicsSystemActivityEntity
    summary: str
    created_at: datetime


class AquaponicsSystemActivityListResponse(BaseModel):
    items: list[AquaponicsSystemActivityRead]
    total: int
    page: int
    page_size: int
