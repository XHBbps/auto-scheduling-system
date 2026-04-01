from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy import String, Numeric, Boolean, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MachineScheduleResult(TimestampMixin, Base):
    __tablename__ = "machine_schedule_result"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_line_id: Mapped[int] = mapped_column(nullable=False)
    contract_no: Mapped[Optional[str]] = mapped_column(String(100))
    customer_name: Mapped[Optional[str]] = mapped_column(String(255))
    product_series: Mapped[Optional[str]] = mapped_column(String(100))
    product_model: Mapped[Optional[str]] = mapped_column(String(100))
    product_name: Mapped[Optional[str]] = mapped_column(String(255))
    material_no: Mapped[Optional[str]] = mapped_column(String(100))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    order_no: Mapped[Optional[str]] = mapped_column(String(100))
    sap_code: Mapped[Optional[str]] = mapped_column(String(100))
    sap_line_no: Mapped[Optional[str]] = mapped_column(String(100))
    delivery_plant: Mapped[Optional[str]] = mapped_column(String(50))
    confirmed_delivery_date: Mapped[Optional[datetime]] = mapped_column()
    drawing_released: Mapped[bool] = mapped_column(Boolean, default=False)
    drawing_release_date: Mapped[Optional[datetime]] = mapped_column()
    schedule_date: Mapped[Optional[datetime]] = mapped_column()
    trigger_date: Mapped[Optional[datetime]] = mapped_column()
    machine_cycle_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    machine_assembly_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    planned_start_date: Mapped[Optional[datetime]] = mapped_column()
    planned_end_date: Mapped[Optional[datetime]] = mapped_column()
    warning_level: Mapped[Optional[str]] = mapped_column(String(50))
    schedule_status: Mapped[Optional[str]] = mapped_column(String(50),
        comment="pending_delivery/pending_drawing/pending_trigger/schedulable/scheduled")
    default_flags: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    issue_flags: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    run_batch_no: Mapped[Optional[str]] = mapped_column(String(100))
    remark: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("order_line_id", name="uk_msr_order_line_id"),
        Index("idx_msr_contract_no", "contract_no"),
        Index("idx_msr_order_no", "order_no"),
        Index("idx_msr_confirmed_delivery_date", "confirmed_delivery_date"),
        Index("idx_msr_schedule_date", "schedule_date"),
        Index("idx_msr_schedule_status", "schedule_status"),
    )
