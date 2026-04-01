from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.common.enums import ScheduleStatus
from app.models.base import Base, TimestampMixin


class OrderScheduleSnapshot(TimestampMixin, Base):
    __tablename__ = "order_schedule_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_line_id: Mapped[int] = mapped_column(nullable=False)

    contract_no: Mapped[Optional[str]] = mapped_column(String(100))
    customer_name: Mapped[Optional[str]] = mapped_column(String(255))
    product_series: Mapped[Optional[str]] = mapped_column(String(100))
    product_model: Mapped[Optional[str]] = mapped_column(String(100))
    product_name: Mapped[Optional[str]] = mapped_column(String(255))
    material_no: Mapped[Optional[str]] = mapped_column(String(100))
    plant: Mapped[Optional[str]] = mapped_column(String(50))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    order_type: Mapped[Optional[str]] = mapped_column(String(50))
    line_total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    order_date: Mapped[Optional[datetime]] = mapped_column()
    business_group: Mapped[Optional[str]] = mapped_column(String(100))
    custom_no: Mapped[Optional[str]] = mapped_column(String(100))
    sales_person_name: Mapped[Optional[str]] = mapped_column(String(100))
    sales_branch_company: Mapped[Optional[str]] = mapped_column(String(100))
    sales_sub_branch: Mapped[Optional[str]] = mapped_column(String(100))
    order_no: Mapped[Optional[str]] = mapped_column(String(100))
    sap_code: Mapped[Optional[str]] = mapped_column(String(100))
    sap_line_no: Mapped[Optional[str]] = mapped_column(String(100))
    confirmed_delivery_date: Mapped[Optional[datetime]] = mapped_column()
    drawing_released: Mapped[bool] = mapped_column(default=False)
    drawing_release_date: Mapped[Optional[datetime]] = mapped_column()
    custom_requirement: Mapped[Optional[str]] = mapped_column(Text)
    review_comment: Mapped[Optional[str]] = mapped_column(Text)

    schedule_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="pending_delivery/pending_drawing/missing_bom/pending_trigger/schedulable/scheduled/scheduled_stale",
    )
    status_reason: Mapped[Optional[str]] = mapped_column(String(255))
    trigger_date: Mapped[Optional[datetime]] = mapped_column()
    machine_cycle_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    is_default_cycle: Mapped[bool] = mapped_column(default=False)

    machine_schedule_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    planned_start_date: Mapped[Optional[datetime]] = mapped_column()
    planned_end_date: Mapped[Optional[datetime]] = mapped_column()
    machine_assembly_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    warning_level: Mapped[Optional[str]] = mapped_column(String(50))
    default_flags: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    issue_flags: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    last_refresh_source: Mapped[Optional[str]] = mapped_column(String(50))
    refresh_reason: Mapped[Optional[str]] = mapped_column(String(255))
    refreshed_at: Mapped[Optional[datetime]] = mapped_column()

    __table_args__ = (
        UniqueConstraint("order_line_id", name="uk_order_schedule_snapshot_order_line_id"),
        Index("idx_order_schedule_snapshot_contract_no", "contract_no"),
        Index("idx_order_schedule_snapshot_order_no", "order_no"),
        Index("idx_order_schedule_snapshot_status", "schedule_status"),
        Index("idx_order_schedule_snapshot_trigger_date", "trigger_date"),
        Index("idx_order_schedule_snapshot_delivery_date", "confirmed_delivery_date"),
        Index("idx_order_schedule_snapshot_product_model", "product_model"),
        Index("idx_order_schedule_snapshot_material_no", "material_no"),
        Index("idx_order_schedule_snapshot_plant", "plant"),
        Index("idx_order_schedule_snapshot_machine_schedule_id", "machine_schedule_id"),
        Index("idx_order_schedule_snapshot_warning_level", "warning_level"),
        Index("ix_order_schedule_snapshot_planned_end_date", "planned_end_date"),
    )

    @staticmethod
    def normalize_schedule_link(
        *,
        schedule_status: str | None,
        machine_schedule_id: int | None,
    ) -> tuple[str | None, int | None]:
        if schedule_status not in {ScheduleStatus.SCHEDULED, ScheduleStatus.SCHEDULED_STALE}:
            return schedule_status, None
        return schedule_status, machine_schedule_id

    @validates("schedule_status")
    def _validate_schedule_status(self, key, value):
        normalized_status, normalized_machine_schedule_id = self.normalize_schedule_link(
            schedule_status=value,
            machine_schedule_id=getattr(self, "machine_schedule_id", None),
        )
        if normalized_machine_schedule_id != getattr(self, "machine_schedule_id", None):
            self.machine_schedule_id = normalized_machine_schedule_id
        return normalized_status

    @validates("machine_schedule_id")
    def _validate_machine_schedule_id(self, key, value):
        _, normalized_machine_schedule_id = self.normalize_schedule_link(
            schedule_status=getattr(self, "schedule_status", None),
            machine_schedule_id=value,
        )
        return normalized_machine_schedule_id
