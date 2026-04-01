from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.datetime_utils import utc_now
from app.models.base import Base


class SyncJobLog(Base):
    __tablename__ = "sync_job_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[datetime] = mapped_column(nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column()
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    operator_name: Mapped[Optional[str]] = mapped_column(String(100))
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    recovered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    recovery_note: Mapped[Optional[str]] = mapped_column(Text)
    message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_sync_job_type", "job_type"),
        Index("idx_sync_source_system", "source_system"),
        Index("idx_sync_start_time", "start_time"),
        Index("idx_sync_status", "status"),
    )
