from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analysis import ErrorInfo

ShortStatus = Literal[
    "queued", "downloading", "preparing", "editing", "rendering", "done", "failed"
]


class ShortCreate(BaseModel):
    analysis_id: str
    template_id: str = "celeb_item"
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)
    recommendation_rank: int | None = None


class ShortOut(BaseModel):
    id: str
    analysis_id: str
    template_id: str
    status: ShortStatus
    stage: str | None
    progress: float
    start_sec: float
    end_sec: float
    edit_version: int
    preview_version: int
    preview_status: str
    warnings: list[str]
    error: ErrorInfo | None
    retry_count: int
    created_at: datetime
    exported_at: datetime | None
