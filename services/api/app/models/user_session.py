from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.datetime_utils import utc_now
from app.models.base import Base


class UserSession(Base):
    __tablename__ = "user_session"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    session_token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)

    user = relationship("UserAccount", back_populates="sessions")

    __table_args__ = (
        Index("idx_user_session_token_hash", "session_token_hash"),
        Index("idx_user_session_user_id", "user_id"),
        Index("idx_user_session_expires_at", "expires_at"),
    )
