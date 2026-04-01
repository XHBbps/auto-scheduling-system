from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RolePermission(Base):
    __tablename__ = "app_role_permission"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("app_role.id", ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[int] = mapped_column(ForeignKey("app_permission.id", ondelete="CASCADE"), nullable=False)

    role = relationship("Role", back_populates="permission_links")
    permission = relationship("Permission", back_populates="role_links")

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_app_role_permission_role_permission"),
        Index("idx_app_role_permission_role_id", "role_id"),
        Index("idx_app_role_permission_permission_id", "permission_id"),
    )
