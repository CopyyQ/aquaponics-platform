from datetime import datetime

from pydantic import BaseModel


class ProjectActivityActor(BaseModel):
    id: int
    name: str


class ProjectActivityEntity(BaseModel):
    type: str
    id: int | None
    name: str


class ProjectActivityRead(BaseModel):
    id: int
    action: str
    actor: ProjectActivityActor
    entity: ProjectActivityEntity
    summary: str
    created_at: datetime


class ProjectActivityListResponse(BaseModel):
    items: list[ProjectActivityRead]
    total: int
    page: int
    page_size: int
