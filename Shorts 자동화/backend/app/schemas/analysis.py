from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AnalysisStatus = Literal["queued", "fetching", "transcribing", "analyzing", "ready", "failed"]


class AnalysisCreate(BaseModel):
    url: str = Field(max_length=2048)
    template_id: str = "celeb_item"


class ErrorInfo(BaseModel):
    code: str
    message: str


class AnalysisOut(BaseModel):
    id: str
    video_id: str
    url: str
    template_id: str
    status: AnalysisStatus
    stage: str | None
    progress: float
    transcript_source: str | None
    warnings: list[str]
    error: ErrorInfo | None
    retry_count: int
    source: dict[str, Any]
    created_at: datetime
    finished_at: datetime | None


class AnalysisList(BaseModel):
    items: list[AnalysisOut]
    next_cursor: str | None


class Sentence(BaseModel):
    id: str
    start_sec: float
    end_sec: float
    text: str


class TranscriptOut(BaseModel):
    source: str
    sentences: list[Sentence]


class WaveformOut(BaseModel):
    duration_sec: float
    peaks_per_sec: int
    peaks: list[float]
