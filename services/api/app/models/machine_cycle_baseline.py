from decimal import Decimal

from sqlalchemy import Boolean, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MachineCycleBaseline(TimestampMixin, Base):
    __tablename__ = "machine_cycle_baseline"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_series: Mapped[str | None] = mapped_column(String(100))
    machine_model: Mapped[str] = mapped_column(String(100), nullable=False)
    order_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cycle_days_median: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_mcb_machine_model", "machine_model"),
        Index("idx_mcb_product_series", "product_series"),
    )
