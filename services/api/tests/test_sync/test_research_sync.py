
import pytest
from unittest.mock import AsyncMock

from app.repository.machine_cycle_history_repo import MachineCycleHistoryRepo
from app.sync.research_data_sync_service import ResearchSyncService


def _make_feishu_record(
    detail_id="DT001",
    material_no="MAT001",
    model="MC1-80",
    qty=2,
    drawing_date=1711900800000,
    inspection_date=1713715200000,
):
    return {
        "record_id": "rec1",
        "fields": {
            "订单编号": [{"text": "SO001"}],
            "明细ID": [{"text": detail_id}],
            "明细-物料编号": [{"text": material_no}],
            "发图时间（研究所）": drawing_date,
            "明细-产品型号": [{"text": model}],
            "产品大系列": "MC1",
            "明细-数量": qty,
            "报检时间": inspection_date,
            "定制编号": [{"text": "CUS001"}],
            "客户名称": [{"text": "客户A"}],
            "合同编号": [{"text": "HT001"}],
            "事业群": "事业群A",
            "订单类型": "常规",
            "最后更新时间": inspection_date,
        },
    }


@pytest.mark.asyncio
async def test_sync_inserts_record(db_session):
    mock_client = AsyncMock()
    mock_client.search_records.return_value = ([_make_feishu_record()], False, "", 1)

    service = ResearchSyncService(
        session=db_session,
        client=mock_client,
        app_token="app123",
        table_id="tbl456",
    )
    result = await service.sync()
    await db_session.commit()

    repo = MachineCycleHistoryRepo(db_session)
    assert await repo.count() == 1
    assert result.insert_count == 1


@pytest.mark.asyncio
async def test_sync_filters_empty_material(db_session):
    record = _make_feishu_record()
    record["fields"]["明细-物料编号"] = [{"text": ""}]

    mock_client = AsyncMock()
    mock_client.search_records.return_value = ([record], False, "", 1)

    service = ResearchSyncService(
        session=db_session,
        client=mock_client,
        app_token="app123",
        table_id="tbl456",
    )
    await service.sync()
    await db_session.commit()

    assert await MachineCycleHistoryRepo(db_session).count() == 0


@pytest.mark.asyncio
async def test_sync_filters_old_records_locally(db_session):
    record = _make_feishu_record()
    record["fields"]["最后更新时间"] = 1710000000000

    mock_client = AsyncMock()
    mock_client.search_records.return_value = ([record], False, "", 1)

    service = ResearchSyncService(
        session=db_session,
        client=mock_client,
        app_token="app123",
        table_id="tbl456",
    )
    result = await service.sync(last_sync_ms=1711000000000)
    await db_session.commit()

    repo = MachineCycleHistoryRepo(db_session)
    assert await repo.count() == 0
    assert result.insert_count == 0


@pytest.mark.asyncio
async def test_sync_filters_order_no_locally(db_session):
    record = _make_feishu_record()

    mock_client = AsyncMock()
    mock_client.search_records.return_value = ([record], False, "", 1)

    service = ResearchSyncService(
        session=db_session,
        client=mock_client,
        app_token="app123",
        table_id="tbl456",
    )
    result = await service.sync(order_no_filter="SO999")
    await db_session.commit()

    repo = MachineCycleHistoryRepo(db_session)
    assert await repo.count() == 0
    assert result.insert_count == 0
