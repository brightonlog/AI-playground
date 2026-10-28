from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    # SQLite drops tzinfo, so store naive UTC and attach UTC on the way out.
    return datetime.now(UTC).replace(tzinfo=None)


ANALYSIS_ACTIVE_STATUSES = ("queued", "fetching", "transcribing", "analyzing")
# "editing" waits on the user, so it does not count toward the active-job cap.
SHORT_ACTIVE_STATUSES = ("queued", "downloading", "preparing", "rendering")


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


class Short(Base):
    __tablename__ = "shorts"

    id: Mapped[str] = mapped_column(String(11), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    template_id: Mapped[str]
    status: Mapped[str] = mapped_column(index=True, default="queued")
    stage: Mapped[str | None]
    start_sec: Mapped[float]
    end_sec: Mapped[float]
    # Source-video time of section.mp4's first frame.
    section_offset_sec: Mapped[float | None]
    edit_version: Mapped[int] = mapped_column(default=0)
    preview_version: Mapped[int] = mapped_column(default=0)
    preview_status: Mapped[str] = mapped_column(default="none")
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    error_code: Mapped[str | None]
    error_message: Mapped[str | None]
    retry_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    exported_at: Mapped[datetime | None]


class SelectionLog(Base):
    """What was recommended vs. what the user chose. Kept when the analysis or short is deleted."""

    __tablename__ = "selection_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[str | None] = mapped_column(ForeignKey("analyses.id"), index=True)
    short_id: Mapped[str | None] = mapped_column(ForeignKey("shorts.id"), index=True)
    video_id: Mapped[str] = mapped_column(String(11))
    recommended: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    chosen_start_sec: Mapped[float]
    chosen_end_sec: Mapped[float]
    recommendation_rank: Mapped[int | None]
    scorer_version: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
