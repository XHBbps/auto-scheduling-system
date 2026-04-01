"""add user identity tables

Revision ID: 20260323_0010
Revises: 20260323_0009
Create Date: 2026-03-23 20:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260323_0010"
down_revision = "20260323_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "app_role" not in existing_tables:
        op.create_table(
            "app_role",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=50), nullable=False),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("code", name="uq_app_role_code"),
        )
        op.create_index("idx_app_role_code", "app_role", ["code"], unique=False)

    if "app_user" not in existing_tables:
        op.create_table(
            "app_user",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("username", sa.String(length=100), nullable=False),
            sa.Column("display_name", sa.String(length=100), nullable=False),
            sa.Column("password_hash", sa.String(length=512), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("last_login_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("username", name="uq_app_user_username"),
        )
        op.create_index("idx_app_user_username", "app_user", ["username"], unique=False)
        op.create_index("idx_app_user_is_active", "app_user", ["is_active"], unique=False)

    if "app_user_role" not in existing_tables:
        op.create_table(
            "app_user_role",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["role_id"], ["app_role.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "role_id", name="uq_app_user_role_user_role"),
        )
        op.create_index("idx_app_user_role_user_id", "app_user_role", ["user_id"], unique=False)
        op.create_index("idx_app_user_role_role_id", "app_user_role", ["role_id"], unique=False)

    if "user_session" not in existing_tables:
        op.create_table(
            "user_session",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("session_token_hash", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("session_token_hash", name="uq_user_session_token_hash"),
        )
        op.create_index("idx_user_session_token_hash", "user_session", ["session_token_hash"], unique=False)
        op.create_index("idx_user_session_user_id", "user_session", ["user_id"], unique=False)
        op.create_index("idx_user_session_expires_at", "user_session", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_user_session_expires_at", table_name="user_session")
    op.drop_index("idx_user_session_user_id", table_name="user_session")
    op.drop_index("idx_user_session_token_hash", table_name="user_session")
    op.drop_table("user_session")

    op.drop_index("idx_app_user_role_role_id", table_name="app_user_role")
    op.drop_index("idx_app_user_role_user_id", table_name="app_user_role")
    op.drop_table("app_user_role")

    op.drop_index("idx_app_user_is_active", table_name="app_user")
    op.drop_index("idx_app_user_username", table_name="app_user")
    op.drop_table("app_user")

    op.drop_index("idx_app_role_code", table_name="app_role")
    op.drop_table("app_role")
