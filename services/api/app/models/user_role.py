from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(Base):
    __tablename__ = "app_user_role"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("app_role.id", ondelete="CASCADE"), nullable=False)

    user = relationship("UserAccount", back_populates="role_links")
    role = relationship("Role", back_populates="user_links")

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_app_user_role_user_role"),
        Index("idx_app_user_role_user_id", "user_id"),
        Index("idx_app_user_role_role_id", "role_id"),
    )
