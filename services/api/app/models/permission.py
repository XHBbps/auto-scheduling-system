from sqlalchemy import Boolean, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Permission(Base, TimestampMixin):
    __tablename__ = "app_permission"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    module_name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    role_links = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_app_permission_code", "code"),
        Index("idx_app_permission_module_name", "module_name"),
        Index("idx_app_permission_is_active", "is_active"),
    )
