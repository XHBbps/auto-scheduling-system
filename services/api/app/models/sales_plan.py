from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, Boolean, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SalesPlanOrderLineSrc(TimestampMixin, Base):
    __tablename__ = "sales_plan_order_line_src"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    contract_no: Mapped[Optional[str]] = mapped_column(String(100))
    crm_no: Mapped[Optional[str]] = mapped_column(String(100))
    customer_name: Mapped[Optional[str]] = mapped_column(String(255))
    custom_no: Mapped[Optional[str]] = mapped_column(String(100))
    sales_person_name: Mapped[Optional[str]] = mapped_column(String(100))
    sales_person_job_no: Mapped[Optional[str]] = mapped_column(String(50))
    product_series: Mapped[Optional[str]] = mapped_column(String(100))
    product_model: Mapped[Optional[str]] = mapped_column(String(100))
    product_name: Mapped[Optional[str]] = mapped_column(String(255))
    material_no: Mapped[Optional[str]] = mapped_column(String(100))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    contract_unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    line_total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    confirmed_delivery_date: Mapped[Optional[datetime]] = mapped_column()
    delivery_date: Mapped[Optional[datetime]] = mapped_column()
    order_type: Mapped[Optional[str]] = mapped_column(String(50), comment="订单类型枚举：1=常规, 2=选配, 3=定制")
    is_automation_project: Mapped[Optional[bool]] = mapped_column(Boolean)
    business_group: Mapped[Optional[str]] = mapped_column(String(100))
    order_date: Mapped[Optional[datetime]] = mapped_column()
    sales_branch_company: Mapped[Optional[str]] = mapped_column(String(100))
    sales_sub_branch: Mapped[Optional[str]] = mapped_column(String(100))
    oa_flow_id: Mapped[Optional[str]] = mapped_column(String(100))
    operator_name: Mapped[Optional[str]] = mapped_column(String(100))
    operator_job_no: Mapped[Optional[str]] = mapped_column(String(50))
    sap_code: Mapped[Optional[str]] = mapped_column(String(100))
    sap_line_no: Mapped[Optional[str]] = mapped_column(String(100))
    delivery_plant: Mapped[Optional[str]] = mapped_column(String(50))
    custom_requirement: Mapped[Optional[str]] = mapped_column(Text)
    review_comment: Mapped[Optional[str]] = mapped_column(Text)
    drawing_released: Mapped[bool] = mapped_column(Boolean, default=False)
    drawing_release_date: Mapped[Optional[datetime]] = mapped_column()
    detail_id: Mapped[Optional[str]] = mapped_column(String(100))
    order_no: Mapped[Optional[str]] = mapped_column(String(100))

    __table_args__ = (
        UniqueConstraint("sap_code", "sap_line_no", name="uk_sales_plan_order_line_src"),
        Index("idx_sales_plan_detail_id", "detail_id"),
        Index("idx_sales_plan_order_no", "order_no"),
        Index("idx_sales_plan_material_no", "material_no"),
        Index("idx_sales_plan_confirmed_delivery_date", "confirmed_delivery_date"),
    )
