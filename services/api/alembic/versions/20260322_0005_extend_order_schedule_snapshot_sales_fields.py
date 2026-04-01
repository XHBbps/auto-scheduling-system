"""extend order schedule snapshot sales fields

Revision ID: 20260322_0005
Revises: 20260321_0004
Create Date: 2026-03-22 00:00:05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260322_0005"
down_revision = "20260321_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("order_schedule_snapshot"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("order_schedule_snapshot")}
    columns_to_add = [
        ("order_type", sa.Column("order_type", sa.String(length=50), nullable=True)),
        ("line_total_amount", sa.Column("line_total_amount", sa.Numeric(18, 4), nullable=True)),
        ("order_date", sa.Column("order_date", sa.DateTime(), nullable=True)),
        ("business_group", sa.Column("business_group", sa.String(length=100), nullable=True)),
        ("custom_no", sa.Column("custom_no", sa.String(length=100), nullable=True)),
        ("sales_person_name", sa.Column("sales_person_name", sa.String(length=100), nullable=True)),
        ("sales_branch_company", sa.Column("sales_branch_company", sa.String(length=100), nullable=True)),
        ("sales_sub_branch", sa.Column("sales_sub_branch", sa.String(length=100), nullable=True)),
        ("sap_code", sa.Column("sap_code", sa.String(length=100), nullable=True)),
        ("sap_line_no", sa.Column("sap_line_no", sa.String(length=100), nullable=True)),
        ("custom_requirement", sa.Column("custom_requirement", sa.Text(), nullable=True)),
        ("review_comment", sa.Column("review_comment", sa.Text(), nullable=True)),
    ]

    for column_name, column in columns_to_add:
        if column_name not in existing_columns:
            op.add_column("order_schedule_snapshot", column)

    op.execute(
        """
        UPDATE order_schedule_snapshot AS snapshot
        SET
            order_type = src.order_type,
            line_total_amount = src.line_total_amount,
            order_date = src.order_date,
            business_group = src.business_group,
            custom_no = src.custom_no,
            sales_person_name = src.sales_person_name,
            sales_branch_company = src.sales_branch_company,
            sales_sub_branch = src.sales_sub_branch,
            sap_code = src.sap_code,
            sap_line_no = src.sap_line_no,
            custom_requirement = src.custom_requirement,
            review_comment = src.review_comment
        FROM sales_plan_order_line_src AS src
        WHERE snapshot.order_line_id = src.id
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("order_schedule_snapshot"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("order_schedule_snapshot")}
    for column_name in [
        "review_comment",
        "custom_requirement",
        "sap_line_no",
        "sap_code",
        "sales_sub_branch",
        "sales_branch_company",
        "sales_person_name",
        "custom_no",
        "business_group",
        "order_date",
        "line_total_amount",
        "order_type",
    ]:
        if column_name in existing_columns:
            op.drop_column("order_schedule_snapshot", column_name)
