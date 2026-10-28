from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    # SQLite drops tzinfo, so store naive UTC and attach UTC on the way out.
    return datetime.now(UTC).replace(tzinfo=None)


ANALYSIS_ACTIVE_STATUSES = ("queued", "fetching", "transcribing", "analyzing")


class Base(DeclarativeBase):
    pass


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(11), primary_key=True)
    video_id: Mapped[str] = mapped_column(String(11), index=True)
    url: Mapped[str]
    template_id: Mapped[str]
    status: Mapped[str] = mapped_column(index=True, default="queued")
    stage: Mapped[str | None]
    progress_weight_mode: Mapped[str] = mapped_column(default="captions")
    transcript_source: Mapped[str | None]
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    error_code: Mapped[str | None]
    error_message: Mapped[str | None]
    retry_count: Mapped[int] = mapped_column(default=0)
    source: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    finished_at: Mapped[datetime | None]
