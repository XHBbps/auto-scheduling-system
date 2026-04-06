from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models.machine_schedule_result import MachineScheduleResult
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.sales_plan_repo import SalesPlanRepo
from app.sync.sales_plan_sync_service import SalesPlanSyncService


@pytest.mark.asyncio
async def test_sync_inserts_records(db_session):
    mock_client = AsyncMock()
    mock_client.fetch_sales_page.side_effect = [
        (
            [
                {
                    "crm_no": "CRM001",
                    "contract_no": "HT001",
                    "customer_name": "客户A",
                    "detail_id": "DT001",
                    "product_model": "MC1-80",
                    "product_series": "MC1",
                    "product_name": "压力机",
                    "material_no": "MAT001",
                    "quantity": "2",
                    "contract_unit_price": "100000",
                    "confirmed_delivery_date": "2026-06-01",
                    "delivery_date": "2026-06-01",
                    "line_total_amount": "200000",
                    "order_no": "SO001",
                    "custom_no": "CUS001",
                    "order_type": "常规",
                    "is_automation_project": "false",
                    "business_group": "事业群A",
                    "sales_person_name": "张三",
                    "sales_person_job_no": "EMP001",
                    "order_date": "2026-03-01",
                    "sales_branch_company": "分公司A",
                    "sales_sub_branch": "支公司A",
                    "sap_code": "SAP001",
                    "sap_line_no": "10",
                    "oa_flow_id": None,
                    "operator_name": None,
                    "operator_job_no": None,
                    "review_comment": None,
                    "custom_requirement": None,
                    "delivery_plant": "1000",
                }
            ],
            1,
        ),
    ]

    service = SalesPlanSyncService(db_session, mock_client)
    result = await service.sync()
    await db_session.commit()

    repo = SalesPlanRepo(db_session)
    count = await repo.count()
    assert count == 1
    assert result.insert_count == 1
    assert result.success_count == 1


@pytest.mark.asyncio
async def test_sync_updates_existing(db_session):
    mock_client = AsyncMock()
    record = {
        "crm_no": "CRM001",
        "contract_no": "HT001",
        "customer_name": "客户A",
        "detail_id": "DT001",
        "product_model": "MC1-80",
        "product_series": "MC1",
        "product_name": "压力机",
        "material_no": "MAT001",
        "quantity": "2",
        "contract_unit_price": None,
        "confirmed_delivery_date": "2026-06-01",
        "delivery_date": None,
        "line_total_amount": None,
        "order_no": "SO001",
        "custom_no": None,
        "order_type": None,
        "is_automation_project": None,
        "business_group": None,
        "sales_person_name": None,
        "sales_person_job_no": None,
        "order_date": None,
        "sales_branch_company": None,
        "sales_sub_branch": None,
        "sap_code": "SAP001",
        "sap_line_no": "10",
        "oa_flow_id": None,
        "operator_name": None,
        "operator_job_no": None,
        "review_comment": None,
        "custom_requirement": None,
        "delivery_plant": None,
    }
    mock_client.fetch_sales_page.side_effect = [
        ([record], 1),
    ]

    service = SalesPlanSyncService(db_session, mock_client)
    await service.sync()
    await db_session.commit()

    # Second sync: update customer name
    record2 = dict(record)
    record2["customer_name"] = "客户B"
    mock_client.fetch_sales_page.side_effect = [([record2], 1)]

    result = await service.sync()
    await db_session.commit()

    repo = SalesPlanRepo(db_session)
    count = await repo.count()
    assert count == 1
    assert result.update_count == 1


@pytest.mark.asyncio
async def test_sync_paginates_when_total_missing_but_page_full(db_session):
    mock_client = AsyncMock()
    page1 = []
    for idx in range(200):
        page1.append(
            {
                "crm_no": f"CRM{idx:03d}",
                "contract_no": f"HT{idx:03d}",
                "customer_name": f"客户{idx}",
                "detail_id": f"DT{idx:03d}",
                "product_model": "MC1-80",
                "product_series": "MC1",
                "product_name": "整机",
                "material_no": f"MAT{idx:03d}",
                "quantity": "1",
                "contract_unit_price": "100000",
                "confirmed_delivery_date": "2026-06-01",
                "delivery_date": "2026-06-01",
                "line_total_amount": "100000",
                "order_no": f"SO{idx:03d}",
                "custom_no": f"CUS{idx:03d}",
                "order_type": "1",
                "is_automation_project": "false",
                "business_group": "BG",
                "sales_person_name": "tester",
                "sales_person_job_no": "EMP001",
                "order_date": "2026-03-01",
                "sales_branch_company": "branch",
                "sales_sub_branch": "sub",
                "sap_code": f"SAP{idx:03d}",
                "sap_line_no": "10",
                "oa_flow_id": None,
                "operator_name": None,
                "operator_job_no": None,
                "review_comment": None,
                "custom_requirement": None,
                "delivery_plant": "1000",
            }
        )
    page2 = [
        {
            **page1[0],
            "crm_no": "CRM200",
            "contract_no": "HT200",
            "customer_name": "客户200",
            "detail_id": "DT200",
            "material_no": "MAT200",
            "order_no": "SO200",
            "custom_no": "CUS200",
            "sap_code": "SAP200",
        }
    ]

    mock_client.fetch_sales_page.side_effect = [
        (page1, 0),
        (page2, 0),
    ]

    service = SalesPlanSyncService(db_session, mock_client)
    result = await service.sync()
    await db_session.commit()

    repo = SalesPlanRepo(db_session)
    count = await repo.count()
    assert count == 201
    assert result.insert_count == 201
    assert mock_client.fetch_sales_page.await_count == 2


@pytest.mark.asyncio
async def test_sync_parses_space_separated_datetime(db_session):
    mock_client = AsyncMock()
    mock_client.fetch_sales_page.side_effect = [
        (
            [
                {
                    "crm_no": "CRM001",
                    "contract_no": "HT001",
                    "customer_name": "客户A",
                    "detail_id": "DT001",
                    "product_model": "MC1-80",
                    "product_series": "MC1",
                    "product_name": "整机",
                    "material_no": "MAT001",
                    "quantity": "2",
                    "contract_unit_price": "100000",
                    "confirmed_delivery_date": "2025-03-28 00:00:00",
                    "delivery_date": "2025-03-29 00:00:00",
                    "line_total_amount": "200000",
                    "order_no": "SO001",
                    "custom_no": "CUS001",
                    "order_type": "1",
                    "is_automation_project": "false",
                    "business_group": "BG",
                    "sales_person_name": "tester",
                    "sales_person_job_no": "EMP001",
                    "order_date": "2025-02-15",
                    "sales_branch_company": "branch",
                    "sales_sub_branch": "sub",
                    "sap_code": "SAP001",
                    "sap_line_no": "10",
                    "oa_flow_id": None,
                    "operator_name": None,
                    "operator_job_no": None,
                    "review_comment": None,
                    "custom_requirement": None,
                    "delivery_plant": "1000",
                }
            ],
            1,
        ),
    ]

    service = SalesPlanSyncService(db_session, mock_client)
    await service.sync()
    await db_session.commit()

    entity = (
        await db_session.execute(select(SalesPlanOrderLineSrc).where(SalesPlanOrderLineSrc.sap_code == "SAP001"))
    ).scalar_one()
    assert entity.confirmed_delivery_date is not None
    assert entity.confirmed_delivery_date.strftime("%Y-%m-%d %H:%M:%S") == "2025-03-28 00:00:00"
    assert entity.delivery_date is not None
    assert entity.delivery_date.strftime("%Y-%m-%d %H:%M:%S") == "2025-03-29 00:00:00"


@pytest.mark.asyncio
async def test_sync_non_critical_change_does_not_trigger_schedule_refresh(db_session):
    mock_client = AsyncMock()
    record = {
        "crm_no": "CRM001",
        "contract_no": "HT001",
        "customer_name": "客户A",
        "detail_id": "DT001",
        "product_model": "MC1-80",
        "product_series": "MC1",
        "product_name": "整机",
        "material_no": "MAT001",
        "quantity": "2",
        "contract_unit_price": None,
        "confirmed_delivery_date": "2026-06-01",
        "delivery_date": None,
        "line_total_amount": None,
        "order_no": "SO001",
        "custom_no": None,
        "order_type": None,
        "is_automation_project": None,
        "business_group": None,
        "sales_person_name": None,
        "sales_person_job_no": None,
        "order_date": None,
        "sales_branch_company": None,
        "sales_sub_branch": None,
        "sap_code": "SAP001",
        "sap_line_no": "10",
        "oa_flow_id": None,
        "operator_name": None,
        "operator_job_no": None,
        "review_comment": None,
        "custom_requirement": None,
        "delivery_plant": None,
    }

    service = SalesPlanSyncService(db_session, mock_client)
    service.schedule_refresh_service.refresh_if_scheduled = AsyncMock()

    mock_client.fetch_sales_page.side_effect = [([record], 1)]
    await service.sync()
    await db_session.commit()

    updated = dict(record)
    updated["customer_name"] = "客户B"
    mock_client.fetch_sales_page.side_effect = [([updated], 1)]
    await service.sync()

    service.schedule_refresh_service.refresh_if_scheduled.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_critical_change_with_existing_schedule_triggers_refresh(db_session):
    mock_client = AsyncMock()
    record = {
        "crm_no": "CRM001",
        "contract_no": "HT001",
        "customer_name": "客户A",
        "detail_id": "DT001",
        "product_model": "MC1-80",
        "product_series": "MC1",
        "product_name": "整机",
        "material_no": "MAT001",
        "quantity": "2",
        "contract_unit_price": None,
        "confirmed_delivery_date": "2026-06-01",
        "delivery_date": None,
        "line_total_amount": None,
        "order_no": "SO001",
        "custom_no": None,
        "order_type": None,
        "is_automation_project": None,
        "business_group": None,
        "sales_person_name": None,
        "sales_person_job_no": None,
        "order_date": None,
        "sales_branch_company": None,
        "sales_sub_branch": None,
        "sap_code": "SAP001",
        "sap_line_no": "10",
        "oa_flow_id": None,
        "operator_name": None,
        "operator_job_no": None,
        "review_comment": None,
        "custom_requirement": None,
        "delivery_plant": None,
    }

    service = SalesPlanSyncService(db_session, mock_client)
    service.schedule_refresh_service.refresh_if_scheduled = AsyncMock()

    mock_client.fetch_sales_page.side_effect = [([record], 1)]
    await service.sync()
    await db_session.commit()

    order = (
        await db_session.execute(select(SalesPlanOrderLineSrc).where(SalesPlanOrderLineSrc.sap_code == "SAP001"))
    ).scalar_one()
    db_session.add(MachineScheduleResult(order_line_id=order.id))
    await db_session.commit()

    updated = dict(record)
    updated["confirmed_delivery_date"] = "2026-06-15"
    mock_client.fetch_sales_page.side_effect = [([updated], 1)]
    await service.sync()

    service.schedule_refresh_service.refresh_if_scheduled.assert_awaited_once_with(
        order_line_id=order.id,
        changed_fields=["confirmed_delivery_date"],
    )
