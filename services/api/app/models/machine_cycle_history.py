from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MachineCycleHistorySrc(TimestampMixin, Base):
    __tablename__ = "machine_cycle_history_src"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    detail_id: Mapped[str] = mapped_column(String(100), nullable=False)
    machine_material_no: Mapped[Optional[str]] = mapped_column(String(100))
    machine_model: Mapped[str] = mapped_column(String(100), nullable=False)
    product_series: Mapped[Optional[str]] = mapped_column(String(100))
    order_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    drawing_release_date: Mapped[Optional[datetime]] = mapped_column()
    inspection_date: Mapped[Optional[datetime]] = mapped_column()
    custom_no: Mapped[Optional[str]] = mapped_column(String(100))
    customer_name: Mapped[Optional[str]] = mapped_column(String(255))
    contract_no: Mapped[Optional[str]] = mapped_column(String(100))
    order_no: Mapped[Optional[str]] = mapped_column(String(100))
    business_group: Mapped[Optional[str]] = mapped_column(String(100))
    order_type: Mapped[Optional[str]] = mapped_column(String(50))
    cycle_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))

    __table_args__ = (
        UniqueConstraint("detail_id", name="uk_machine_cycle_history_detail_id"),
        Index("idx_mch_machine_model", "machine_model"),
        Index("idx_mch_machine_material_no", "machine_material_no"),
        Index("idx_mch_order_no", "order_no"),
    )
