from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ProductionOrderHistorySrc(TimestampMixin, Base):
    __tablename__ = "production_order_history_src"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    production_order_no: Mapped[str] = mapped_column(String(100), nullable=False)
    material_no: Mapped[Optional[str]] = mapped_column(String(100))
    material_desc: Mapped[Optional[str]] = mapped_column(String(255))
    machine_model: Mapped[Optional[str]] = mapped_column(String(100))
    plant: Mapped[Optional[str]] = mapped_column(String(50))
    processing_dept: Mapped[Optional[str]] = mapped_column(String(100))
    start_time_actual: Mapped[Optional[datetime]] = mapped_column()
    finish_time_actual: Mapped[Optional[datetime]] = mapped_column()
    production_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    order_status: Mapped[Optional[str]] = mapped_column(String(50))
    sales_order_no: Mapped[Optional[str]] = mapped_column(String(100))
    created_time_src: Mapped[Optional[datetime]] = mapped_column()
    last_modified_time_src: Mapped[Optional[datetime]] = mapped_column()

    __table_args__ = (
        UniqueConstraint("production_order_no", name="uk_production_order_history_src"),
        Index("idx_prod_order_material_no", "material_no"),
        Index("idx_prod_order_machine_model", "machine_model"),
        Index("idx_prod_order_last_modified", "last_modified_time_src"),
    )
