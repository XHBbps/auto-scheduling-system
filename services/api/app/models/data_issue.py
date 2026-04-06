from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.models.base import Base, TimestampMixin


class DataIssueRecord(TimestampMixin, Base):
    __tablename__ = "data_issue_record"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    issue_level: Mapped[str | None] = mapped_column(String(50))
    source_system: Mapped[str | None] = mapped_column(String(50))
    biz_key: Mapped[str | None] = mapped_column(String(200))
    order_line_id: Mapped[int | None] = mapped_column(ForeignKey("sales_plan_order_line_src.id", ondelete="SET NULL"))
    issue_title: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_detail: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    handler: Mapped[str | None] = mapped_column(String(100))
    handled_at: Mapped[datetime | None] = mapped_column()
    remark: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_issue_type", "issue_type"),
        Index("idx_issue_status", "status"),
        Index("idx_issue_biz_key", "biz_key"),
        Index("idx_issue_order_line_id", "order_line_id"),
    )

    @staticmethod
    def normalize_order_link(
        *,
        biz_key: str | None,
        order_line_id: int | None,
    ) -> tuple[str | None, int | None]:
        if order_line_id is None:
            return biz_key, None

        expected_biz_key = str(order_line_id)
        if biz_key is None or not str(biz_key).strip():
            return expected_biz_key, order_line_id
        if str(biz_key) != expected_biz_key:
            raise ValueError("biz_key does not match order_line_id")
        return expected_biz_key, order_line_id

    @staticmethod
    def normalize_source_system(source_system: str | None) -> str | None:
        value = (source_system or "").strip()
        return value or None

    @validates("order_line_id")
    def _validate_order_line_id(self, key, value):
        normalized_biz_key, normalized_order_line_id = self.normalize_order_link(
            biz_key=getattr(self, "biz_key", None),
            order_line_id=value,
        )
        if normalized_biz_key != getattr(self, "biz_key", None):
            self.biz_key = normalized_biz_key
        return normalized_order_line_id

    @validates("biz_key")
    def _validate_biz_key(self, key, value):
        normalized_biz_key, _ = self.normalize_order_link(
            biz_key=value,
            order_line_id=getattr(self, "order_line_id", None),
        )
        return normalized_biz_key

    @validates("source_system")
    def _validate_source_system(self, key, value):
        return self.normalize_source_system(value)
