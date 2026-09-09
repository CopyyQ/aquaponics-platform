from datetime import datetime

from pydantic import BaseModel


class AquaponicsSystemActivityActor(BaseModel):
    id: int
    name: str


class AquaponicsSystemActivityEntity(BaseModel):
    type: str
    id: int | None
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
