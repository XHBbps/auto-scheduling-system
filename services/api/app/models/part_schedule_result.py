from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PartScheduleResult(TimestampMixin, Base):
    __tablename__ = "part_schedule_result"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_line_id: Mapped[int] = mapped_column(
        ForeignKey("sales_plan_order_line_src.id", ondelete="CASCADE"), nullable=False
    )
    machine_schedule_id: Mapped[int | None] = mapped_column(ForeignKey("machine_schedule_result.id"))
    assembly_name: Mapped[str] = mapped_column(String(100), nullable=False)
    production_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    assembly_time_days: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    assembly_is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_material_no: Mapped[str | None] = mapped_column(String(100))
    parent_name: Mapped[str | None] = mapped_column(String(255))
    node_level: Mapped[int | None] = mapped_column(Integer)
    bom_path: Mapped[str | None] = mapped_column(Text)
    bom_path_key: Mapped[str | None] = mapped_column(String(500))
    part_material_no: Mapped[str | None] = mapped_column(String(100))
    part_name: Mapped[str | None] = mapped_column(String(255))
    part_raw_material_desc: Mapped[str | None] = mapped_column(String(255))
    is_key_part: Mapped[bool] = mapped_column(Boolean, default=False)
    part_cycle_days: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    part_cycle_is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    part_cycle_match_rule: Mapped[str | None] = mapped_column(String(100))
    key_part_material_no: Mapped[str | None] = mapped_column(String(100))
    key_part_name: Mapped[str | None] = mapped_column(String(255))
    key_part_raw_material_desc: Mapped[str | None] = mapped_column(String(255))
    key_part_cycle_days: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    key_part_is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    cycle_match_rule: Mapped[str | None] = mapped_column(String(100))
    planned_start_date: Mapped[datetime | None] = mapped_column()
    planned_end_date: Mapped[datetime | None] = mapped_column()
    warning_level: Mapped[str | None] = mapped_column(String(50))
    default_flags: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    issue_flags: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    run_batch_no: Mapped[str | None] = mapped_column(String(100))
    remark: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_psr_order_line_id", "order_line_id"),
        Index("idx_psr_machine_schedule_id", "machine_schedule_id"),
        Index("idx_psr_assembly_name", "assembly_name"),
        Index("idx_psr_production_sequence", "production_sequence"),
        Index("idx_psr_parent_material_no", "parent_material_no"),
        Index("idx_psr_bom_path_key", "bom_path_key"),
    )
