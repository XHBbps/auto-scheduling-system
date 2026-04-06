from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.datetime_utils import utc_now
from app.models.base import Base, TimestampMixin


class BackgroundTask(TimestampMixin, Base):
    __tablename__ = "background_task"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="manual_api")
    reason: Mapped[str | None] = mapped_column(String(120))
    dedupe_key: Mapped[str | None] = mapped_column(String(160))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    sync_job_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("sync_job_log.id", ondelete="SET NULL"),
        nullable=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    available_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    worker_id: Mapped[str | None] = mapped_column(String(120))
    last_error: Mapped[str | None] = mapped_column(Text)
    dead_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    __table_args__ = (
        Index("idx_background_task_status_available", "status", "available_at", "id"),
        Index("idx_background_task_dedupe_key", "dedupe_key"),
        Index("idx_background_task_sync_job_log_id", "sync_job_log_id"),
        Index("idx_background_task_task_type", "task_type"),
    )
