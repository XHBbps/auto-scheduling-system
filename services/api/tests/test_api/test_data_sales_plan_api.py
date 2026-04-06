from datetime import datetime
from decimal import Decimal

import pytest

from app.models.sales_plan import SalesPlanOrderLineSrc


@pytest.mark.asyncio
async def test_list_sales_plan_orders_returns_extended_fields(app_client, db_session):
    db_session.add(
        SalesPlanOrderLineSrc(
            contract_no="HT001",
            customer_name="客户A",
            product_series="MC",
            product_model="MC-100",
            product_name="数控冲床",
            material_no="MAT-001",
            quantity=Decimal("2"),
            line_total_amount=Decimal("880000"),
            confirmed_delivery_date=datetime(2026, 4, 20, 0, 0, 0),
            order_date=datetime(2026, 3, 1, 0, 0, 0),
            order_type="1",
            business_group="装备事业群",
            custom_no="DZ-001",
            sales_person_name="张三",
            sales_branch_company="华东分公司",
            sales_sub_branch="苏州支公司",
            drawing_released=True,
            custom_requirement="需要自动上料",
            review_comment="优先排产",
            order_no="SO-001",
            sap_code="SAP-001",
            sap_line_no="10",
        )
    )
    await db_session.commit()

    resp = await app_client.get("/api/data/sales-plan-orders")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["total"] == 1
    item = body["data"]["items"][0]
    assert item["product_name"] == "数控冲床"
    assert item["line_total_amount"] == 880000.0
    assert item["business_group"] == "装备事业群"
    assert item["custom_no"] == "DZ-001"
    assert item["sales_person_name"] == "张三"
    assert item["order_date"] == "2026-03-01T00:00:00"
    assert item["sales_branch_company"] == "华东分公司"
    assert item["sales_sub_branch"] == "苏州支公司"
    assert item["custom_requirement"] == "需要自动上料"
    assert item["review_comment"] == "优先排产"


@pytest.mark.asyncio
async def test_list_sales_plan_orders_supports_org_filters(app_client, db_session):
    db_session.add_all(
        [
            SalesPlanOrderLineSrc(
                contract_no="HT001",
                customer_name="客户A",
                product_series="MC",
                product_model="MC-100",
                material_no="MAT-001",
                business_group="装备事业群",
                sales_branch_company="华东分公司",
                sales_sub_branch="苏州支公司",
            ),
            SalesPlanOrderLineSrc(
                contract_no="HT002",
                customer_name="客户B",
                product_series="JC",
                product_model="JC-80",
                material_no="MAT-002",
                business_group="扬机事业群",
                sales_branch_company="华南分公司",
                sales_sub_branch="佛山支公司",
            ),
        ]
    )
    await db_session.commit()

    resp = await app_client.get(
        "/api/data/sales-plan-orders",
        params={
            "business_group": "装备",
            "sales_branch_company": "华东",
            "sales_sub_branch": "苏州",
        },
    )
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["total"] == 1
    item = body["data"]["items"][0]
    assert item["contract_no"] == "HT001"
    assert item["business_group"] == "装备事业群"
    assert item["sales_branch_company"] == "华东分公司"
    assert item["sales_sub_branch"] == "苏州支公司"


@pytest.mark.asyncio
async def test_get_sales_plan_org_filter_options_returns_trimmed_distinct_values(app_client, db_session):
    db_session.add_all(
        [
            SalesPlanOrderLineSrc(
                contract_no="HT001",
                customer_name="客户A",
                product_series="MC",
                product_model="MC-100",
                material_no="MAT-001",
                business_group="装备事业群",
                sales_branch_company="华东分公司 ",
                sales_sub_branch="苏州支公司",
            ),
            SalesPlanOrderLineSrc(
                contract_no="HT002",
                customer_name="客户B",
                product_series="JC",
                product_model="JC-80",
                material_no="MAT-002",
                business_group="装备事业群 ",
                sales_branch_company="华东分公司",
                sales_sub_branch="苏州支公司 ",
            ),
            SalesPlanOrderLineSrc(
                contract_no="HT003",
                customer_name="客户C",
                product_series="JF",
                product_model="JF-45",
                material_no="MAT-003",
                business_group=None,
                sales_branch_company="",
                sales_sub_branch="  ",
            ),
        ]
    )
    await db_session.commit()

    resp = await app_client.get("/api/data/sales-plan-orders/options/org-filters")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"] == {
        "business_groups": ["装备事业群"],
        "sales_branch_companies": ["华东分公司"],
        "sales_sub_branches": ["苏州支公司"],
    }


@pytest.mark.asyncio
async def test_list_sales_plan_orders_supports_sorting_extended_fields(app_client, db_session):
    db_session.add_all(
        [
            SalesPlanOrderLineSrc(
                contract_no="HT001",
                customer_name="客户A",
                product_series="MC",
                product_model="MC-100",
                product_name="折弯机",
                material_no="MAT-001",
                quantity=Decimal("2"),
                line_total_amount=Decimal("100"),
                order_date=datetime(2026, 3, 1, 0, 0, 0),
                business_group="装备事业群",
                custom_no="DZ-001",
                sales_person_name="张三",
                sales_branch_company="华东分公司",
                sales_sub_branch="苏州支公司",
                custom_requirement="A类要求",
                review_comment="甲备注",
            ),
            SalesPlanOrderLineSrc(
                contract_no="HT002",
                customer_name="客户B",
                product_series="JC",
                product_model="JC-80",
                product_name="冲床",
                material_no="MAT-002",
                quantity=Decimal("1"),
                line_total_amount=Decimal("200"),
                order_date=datetime(2026, 4, 1, 0, 0, 0),
                business_group="扬机事业群",
                custom_no="DZ-002",
                sales_person_name="李四",
                sales_branch_company="华南分公司",
                sales_sub_branch="佛山支公司",
                custom_requirement="B类要求",
                review_comment="乙备注",
            ),
        ]
    )
    await db_session.commit()

    resp = await app_client.get(
        "/api/data/sales-plan-orders",
        params={"sort_field": "line_total_amount", "sort_order": "desc"},
    )
    body = resp.json()
    assert body["code"] == 0
    assert [item["contract_no"] for item in body["data"]["items"]] == ["HT002", "HT001"]

    resp = await app_client.get(
        "/api/data/sales-plan-orders",
        params={"sort_field": "custom_requirement", "sort_order": "asc"},
    )
    body = resp.json()
    assert body["code"] == 0
    assert [item["contract_no"] for item in body["data"]["items"]] == ["HT001", "HT002"]
