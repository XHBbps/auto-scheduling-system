from unittest.mock import AsyncMock

import pytest

from app.repository.production_order_repo import ProductionOrderRepo
from app.sync.production_order_sync_service import ProductionOrderSyncService


def _make_po_record(
    order_no="PO001", material_no="MAT001", status="已完工", start_ms=1711900800000, finish_ms=1713715200000
):
    return {
        "record_id": "rec1",
        "fields": {
            "生产订单号": [{"text": order_no}],
            "物料号": [{"text": material_no}],
            "物料描述": [{"text": "部件A"}],
            "机床型号": [{"text": "MC1-80"}],
            "生产工厂": [{"text": "1000"}],
            "加工部门": "车间一",
            "投产时间": start_ms,
            "完工时间": finish_ms,
            "订货数量": 5,
            "生产订单状态": status,
            "销售订单号": [{"text": "SO001"}],
            "创建时间": 1711900800000,
            "最后更新时间": 1713715200000,
        },
    }


@pytest.mark.asyncio
async def test_sync_inserts_record(db_session):
    mock_client = AsyncMock()
    mock_client.search_records.return_value = ([_make_po_record()], False, "", 1)

    service = ProductionOrderSyncService(
        session=db_session,
        client=mock_client,
        app_token="app123",
        table_id="tbl456",
    )
    result = await service.sync()
    await db_session.commit()

    repo = ProductionOrderRepo(db_session)
    count = await repo.count()
    assert count == 1
    assert result.insert_count == 1


@pytest.mark.asyncio
async def test_sync_upserts_duplicate(db_session):
    mock_client = AsyncMock()
    mock_client.search_records.return_value = ([_make_po_record(), _make_po_record()], False, "", 2)

    service = ProductionOrderSyncService(
        session=db_session,
        client=mock_client,
        app_token="app123",
        table_id="tbl456",
    )
    result = await service.sync()
    await db_session.commit()

    repo = ProductionOrderRepo(db_session)
    count = await repo.count()
    assert count == 1
    assert result.issue_count >= 1  # duplicate recorded as issue


@pytest.mark.asyncio
async def test_sync_filters_old_records_locally(db_session):
    mock_client = AsyncMock()
    old_record = _make_po_record()
    old_record["fields"]["最后更新时间"] = 1710000000000
    mock_client.search_records.return_value = ([old_record], False, "", 1)

    service = ProductionOrderSyncService(
        session=db_session,
        client=mock_client,
        app_token="app123",
        table_id="tbl456",
    )
    result = await service.sync(last_sync_ms=1711000000000)
    await db_session.commit()

    repo = ProductionOrderRepo(db_session)
    assert await repo.count() == 0
    assert result.insert_count == 0
