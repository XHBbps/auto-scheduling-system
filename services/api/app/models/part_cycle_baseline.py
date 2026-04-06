from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PartCycleBaseline(TimestampMixin, Base):
    __tablename__ = "part_cycle_baseline"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_no: Mapped[str] = mapped_column(String(100), nullable=False)
    material_desc: Mapped[str] = mapped_column(String(255), nullable=False)
    core_part_name: Mapped[str] = mapped_column(String(100), nullable=False)
    machine_model: Mapped[str | None] = mapped_column(String(100))
    plant: Mapped[str | None] = mapped_column(String(50))
    ref_batch_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cycle_days: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cycle_days: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    sample_count: Mapped[int] = mapped_column(default=0, nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    cycle_source: Mapped[str | None] = mapped_column(String(50))
    match_rule: Mapped[str | None] = mapped_column(String(100))
    confidence_level: Mapped[str | None] = mapped_column(String(50))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("material_no", "machine_model", "plant", name="uq_pcb_material_machine_plant"),
        Index(
            "uq_pcb_material_machine_null_plant",
            "material_no",
            "machine_model",
            unique=True,
            postgresql_where=text("plant IS NULL"),
            sqlite_where=text("plant IS NULL"),
        ),
        Index("idx_pcb_material_no", "material_no"),
        Index("idx_pcb_core_part_name", "core_part_name"),
        Index("idx_pcb_machine_model", "machine_model"),
        Index("idx_pcb_plant", "plant"),
        Index("idx_pcb_source_active", "cycle_source", "is_active"),
    )
