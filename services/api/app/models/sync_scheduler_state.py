from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.common.datetime_utils import utc_now
from app.models.base import Base


class SyncSchedulerState(Base):
    __tablename__ = "sync_scheduler_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_state: Mapped[str] = mapped_column(String(50), nullable=False, default="stopped")
    instance_id: Mapped[Optional[str]] = mapped_column(String(120))
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_by: Mapped[Optional[str]] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, server_default=func.now(), onupdate=utc_now, nullable=False)
