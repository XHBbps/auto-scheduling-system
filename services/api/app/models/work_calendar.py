from datetime import date
from typing import Optional
from sqlalchemy import Date, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class WorkCalendar(TimestampMixin, Base):
    __tablename__ = "work_calendar"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    calendar_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_workday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("calendar_date", name="uk_work_calendar"),
    )
