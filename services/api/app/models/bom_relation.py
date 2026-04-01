from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, Boolean, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BomRelationSrc(TimestampMixin, Base):
    __tablename__ = "bom_relation_src"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    machine_material_no: Mapped[str] = mapped_column(String(100), nullable=False)
    machine_material_desc: Mapped[Optional[str]] = mapped_column(String(255))
    plant: Mapped[Optional[str]] = mapped_column(String(50))
    material_no: Mapped[Optional[str]] = mapped_column(String(100))
    material_desc: Mapped[Optional[str]] = mapped_column(String(255))
    bom_component_no: Mapped[Optional[str]] = mapped_column(String(100))
    bom_component_desc: Mapped[Optional[str]] = mapped_column(String(255))
    part_type: Mapped[Optional[str]] = mapped_column(String(50))
    component_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    bom_level: Mapped[Optional[int]] = mapped_column(Integer)
    is_top_level: Mapped[bool] = mapped_column(Boolean, default=False)
    is_self_made: Mapped[bool] = mapped_column(Boolean, default=False)
    sync_time: Mapped[Optional[datetime]] = mapped_column()

    __table_args__ = (
        Index("idx_bom_machine_material_no", "machine_material_no"),
        Index("idx_bom_component_no", "bom_component_no"),
        Index("idx_bom_part_type", "part_type"),
        Index("idx_bom_machine_material_material_no", "machine_material_no", "material_no"),
        Index("idx_bom_machine_material_component_no", "machine_material_no", "bom_component_no"),
    )
