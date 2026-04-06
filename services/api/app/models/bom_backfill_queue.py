from datetime import datetime

from sqlalchemy import Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.datetime_utils import utc_now
from app.models.base import Base, TimestampMixin


class BomBackfillQueue(TimestampMixin, Base):
    __tablename__ = "bom_backfill_queue"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_no: Mapped[str] = mapped_column(String(100), nullable=False)
    plant: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_reason: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_kind: Mapped[str | None] = mapped_column(String(50))
    last_error: Mapped[str | None] = mapped_column(Text)
    next_retry_at: Mapped[datetime | None] = mapped_column()
    first_detected_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column()
    resolved_at: Mapped[datetime | None] = mapped_column()
    last_job_id: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("material_no", "plant", name="uk_bom_backfill_queue_material_plant"),
        Index("idx_bom_backfill_queue_status_retry", "status", "next_retry_at", "priority", "id"),
        Index("idx_bom_backfill_queue_source_status", "source", "status"),
        Index("idx_bom_backfill_queue_updated_at", "updated_at"),
    )
