"""add admin session and sync job recovery fields

Revision ID: 20260323_0008
Revises: 20260323_0007
Create Date: 2026-03-23 00:00:08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260323_0008"
down_revision = "20260323_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_tables = set(inspector.get_table_names())
    if "admin_session" not in existing_tables:
        op.create_table(
            "admin_session",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("session_token", sa.String(length=128), nullable=False, unique=True),
            sa.Column("operator_name", sa.String(length=100), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
        )
        op.create_index("idx_admin_session_token", "admin_session", ["session_token"], unique=False)
        op.create_index("idx_admin_session_expires_at", "admin_session", ["expires_at"], unique=False)

    if "sync_job_log" in existing_tables:
        sync_columns = {column["name"] for column in inspector.get_columns("sync_job_log")}
        sync_indexes = {index["name"] for index in inspector.get_indexes("sync_job_log")}

        column_defs = [
            ("operator_name", sa.String(length=100), True),
            ("timeout_seconds", sa.Integer(), False),
            ("heartbeat_at", sa.DateTime(), True),
            ("recovered_at", sa.DateTime(), True),
            ("recovery_note", sa.Text(), True),
        ]
        for name, column_type, nullable in column_defs:
            if name not in sync_columns:
                server_default = sa.text("0") if name == "timeout_seconds" else None
                op.add_column(
                    "sync_job_log",
                    sa.Column(name, column_type, nullable=nullable, server_default=server_default),
                )
        if "idx_sync_status" not in sync_indexes:
            op.create_index("idx_sync_status", "sync_job_log", ["status"], unique=False)

    if "data_issue_record" in existing_tables:
        issue_columns = {column["name"] for column in inspector.get_columns("data_issue_record")}
        issue_indexes = {index["name"] for index in inspector.get_indexes("data_issue_record")}

        if "order_line_id" not in issue_columns:
            op.add_column("data_issue_record", sa.Column("order_line_id", sa.Integer(), nullable=True))
        if "idx_issue_order_line_id" not in issue_indexes:
            op.create_index("idx_issue_order_line_id", "data_issue_record", ["order_line_id"], unique=False)

        dialect_name = bind.dialect.name
        if dialect_name == "postgresql":
            op.execute(
                """
                UPDATE data_issue_record
                SET order_line_id = CAST(biz_key AS INTEGER)
                WHERE order_line_id IS NULL
                  AND biz_key IS NOT NULL
                  AND biz_key ~ '^[0-9]+$'
                """
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "data_issue_record" in existing_tables:
        issue_columns = {column["name"] for column in inspector.get_columns("data_issue_record")}
        issue_indexes = {index["name"] for index in inspector.get_indexes("data_issue_record")}
        if "idx_issue_order_line_id" in issue_indexes:
            op.drop_index("idx_issue_order_line_id", table_name="data_issue_record")
        if "order_line_id" in issue_columns:
            op.drop_column("data_issue_record", "order_line_id")

    if "sync_job_log" in existing_tables:
        sync_columns = {column["name"] for column in inspector.get_columns("sync_job_log")}
        sync_indexes = {index["name"] for index in inspector.get_indexes("sync_job_log")}
        if "idx_sync_status" in sync_indexes:
            op.drop_index("idx_sync_status", table_name="sync_job_log")
        for column_name in [
            "recovery_note",
            "recovered_at",
            "heartbeat_at",
            "timeout_seconds",
            "operator_name",
        ]:
            if column_name in sync_columns:
                op.drop_column("sync_job_log", column_name)

    if "admin_session" in existing_tables:
        admin_indexes = {index["name"] for index in inspector.get_indexes("admin_session")}
        for index_name in [
            "idx_admin_session_expires_at",
            "idx_admin_session_token",
        ]:
            if index_name in admin_indexes:
                op.drop_index(index_name, table_name="admin_session")
        op.drop_table("admin_session")
