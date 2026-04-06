from decimal import Decimal

from sqlalchemy import Boolean, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AssemblyTimeBaseline(TimestampMixin, Base):
    __tablename__ = "assembly_time_baseline"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    machine_model: Mapped[str] = mapped_column(String(100), nullable=False)
    product_series: Mapped[str | None] = mapped_column(String(100))
    assembly_name: Mapped[str] = mapped_column(String(100), nullable=False)
    assembly_time_days: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    is_final_assembly: Mapped[bool] = mapped_column(Boolean, default=False)
    production_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    remark: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_atb_machine_model", "machine_model"),
        Index("idx_atb_product_series", "product_series"),
        Index("idx_atb_assembly_name", "assembly_name"),
    )
