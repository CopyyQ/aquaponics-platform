from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class DisableReasonRequest(BaseModel):
    reason: str


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
