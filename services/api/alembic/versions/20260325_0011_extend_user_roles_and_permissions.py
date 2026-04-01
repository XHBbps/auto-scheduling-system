"""extend user roles and permission skeleton

Revision ID: 20260325_0011
Revises: 20260323_0010
Create Date: 2026-03-25 14:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260325_0011"
down_revision = "20260323_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "app_role" in existing_tables:
        role_columns = {col["name"] for col in inspector.get_columns("app_role")}
        role_indexes = {idx["name"] for idx in inspector.get_indexes("app_role")}
        if "description" not in role_columns:
            op.add_column("app_role", sa.Column("description", sa.String(length=200), nullable=True))
        if "is_active" not in role_columns:
            op.add_column("app_role", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
        if "idx_app_role_is_active" not in role_indexes:
            op.create_index("idx_app_role_is_active", "app_role", ["is_active"], unique=False)

    if "app_permission" not in existing_tables:
        op.create_table(
            "app_permission",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("module_name", sa.String(length=80), nullable=False),
            sa.Column("description", sa.String(length=200), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("code", name="uq_app_permission_code"),
        )
        op.create_index("idx_app_permission_code", "app_permission", ["code"], unique=False)
        op.create_index("idx_app_permission_module_name", "app_permission", ["module_name"], unique=False)
        op.create_index("idx_app_permission_is_active", "app_permission", ["is_active"], unique=False)

    if "app_role_permission" not in existing_tables:
        op.create_table(
            "app_role_permission",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.Column("permission_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["role_id"], ["app_role.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["permission_id"], ["app_permission.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("role_id", "permission_id", name="uq_app_role_permission_role_permission"),
        )
        op.create_index("idx_app_role_permission_role_id", "app_role_permission", ["role_id"], unique=False)
        op.create_index("idx_app_role_permission_permission_id", "app_role_permission", ["permission_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_app_role_permission_permission_id", table_name="app_role_permission")
    op.drop_index("idx_app_role_permission_role_id", table_name="app_role_permission")
    op.drop_table("app_role_permission")

    op.drop_index("idx_app_permission_is_active", table_name="app_permission")
    op.drop_index("idx_app_permission_module_name", table_name="app_permission")
    op.drop_index("idx_app_permission_code", table_name="app_permission")
    op.drop_table("app_permission")

    op.drop_index("idx_app_role_is_active", table_name="app_role")
    op.drop_column("app_role", "is_active")
    op.drop_column("app_role", "description")
