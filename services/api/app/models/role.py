from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Role(Base, TimestampMixin):
    __tablename__ = "app_role"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user_links = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    permission_links = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_app_role_code", "code"),
        Index("idx_app_role_is_active", "is_active"),
    )
