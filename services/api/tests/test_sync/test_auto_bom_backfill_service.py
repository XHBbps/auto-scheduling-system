from datetime import datetime
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy import event, select

from app.common.enums import BomBackfillQueueStatus
from app.models.bom_backfill_queue import BomBackfillQueue
from app.models.bom_relation import BomRelationSrc
from app.models.data_issue import DataIssueRecord
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.sync_job_log import SyncJobLog
from app.repository.bom_backfill_queue_repo import BomBackfillQueueRepo
from app.sync.auto_bom_backfill_service import AutoBomBackfillService


class _SessionFactory:
    def __init__(self, session):
        self.session = session

    def __call__(self):
        session = self.session

        class _SessionContext:
            async def __aenter__(self_inner):
                return session

            async def __aexit__(self_inner, exc_type, exc, tb):
                return False

        return _SessionContext()


@pytest.mark.asyncio
async def test_auto_bom_backfill_enqueues_missing_materials(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP-BOM-001",
        sap_line_no="10",
        order_no="SO-BOM-001",
        material_no="MAT-BOM-001",
        delivery_plant="1100",
        drawing_released=True,
        confirmed_delivery_date=datetime(2026, 4, 1),
    )
    db_session.add(order)
    await db_session.commit()

    service = AutoBomBackfillService(session_factory=_SessionFactory(db_session))
    result = await service.run(
        source="sales_plan_sync",
        reason="sales_plan_or_drawing_updated",
        order_line_ids=[order.id],
        sap_bom_base_url="https://sap.example.com",
    )

    queue_items = (
        await db_session.execute(select(BomBackfillQueue).where(BomBackfillQueue.material_no == "MAT-BOM-001"))
    ).scalars().all()

    assert result.candidate_orders == 1
    assert result.candidate_items == 1
    assert result.enqueued_items == 1
    assert result.reactivated_items == 0
    assert result.already_tracked_items == 0
    assert len(queue_items) == 1
    assert queue_items[0].status == BomBackfillQueueStatus.PENDING.value


@pytest.mark.asyncio
async def test_auto_bom_backfill_reactivates_retry_wait_item(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP-BOM-002",
        sap_line_no="20",
        order_no="SO-BOM-002",
        material_no="MAT-BOM-002",
        delivery_plant="1100",
        drawing_released=True,
        confirmed_delivery_date=datetime(2026, 4, 2),
    )
    db_session.add(order)
    await db_session.flush()
    db_session.add(
        BomBackfillQueue(
            material_no="MAT-BOM-002",
            plant="1100",
            source="sales_plan_sync",
            trigger_reason="old_reason",
            status=BomBackfillQueueStatus.RETRY_WAIT.value,
            fail_count=2,
        )
    )
    await db_session.commit()

    service = AutoBomBackfillService(session_factory=_SessionFactory(db_session))
    result = await service.run(
        source="research_sync",
        reason="drawing_status_backfill",
        sap_bom_base_url="https://sap.example.com",
    )

    queue_item = (
        await db_session.execute(select(BomBackfillQueue).where(BomBackfillQueue.material_no == "MAT-BOM-002"))
    ).scalar_one()

    assert result.enqueued_items == 0
    assert result.reactivated_items == 1
    assert queue_item.status == BomBackfillQueueStatus.PENDING.value
    assert queue_item.fail_count == 0
    assert queue_item.source == "research_sync"


@pytest.mark.asyncio
async def test_auto_bom_backfill_enqueues_multiple_candidates_without_per_item_lookup(db_session, monkeypatch):
    orders = [
        SalesPlanOrderLineSrc(
            sap_code="SAP-BOM-BATCH-001",
            sap_line_no="10",
            order_no="SO-BATCH-001",
            material_no="MAT-BATCH-001",
            delivery_plant="1100",
            drawing_released=True,
            confirmed_delivery_date=datetime(2026, 4, 4),
        ),
        SalesPlanOrderLineSrc(
            sap_code="SAP-BOM-BATCH-002",
            sap_line_no="20",
            order_no="SO-BATCH-002",
            material_no="MAT-BATCH-002",
            delivery_plant="1200",
            drawing_released=True,
            confirmed_delivery_date=datetime(2026, 4, 5),
        ),
    ]
    db_session.add_all(orders)
    await db_session.commit()

    original_batch_lookup = BomBackfillQueueRepo.find_by_material_plants

    async def fail_single_lookup(self, material_no, plant):
        raise AssertionError("enqueue_candidates should not query queue items one by one")

    batch_lookup_calls = 0

    async def track_batch_lookup(self, items):
        nonlocal batch_lookup_calls
        batch_lookup_calls += 1
        return await original_batch_lookup(self, items)

    monkeypatch.setattr(BomBackfillQueueRepo, "get_by_material_and_plant", fail_single_lookup)
    monkeypatch.setattr(BomBackfillQueueRepo, "find_by_material_plants", track_batch_lookup)

    service = AutoBomBackfillService(session_factory=_SessionFactory(db_session))
    result = await service.run(
        source="sales_plan_sync",
        reason="sales_plan_or_drawing_updated",
        sap_bom_base_url="https://sap.example.com",
    )

    assert result.candidate_orders == 2
    assert result.enqueued_items == 2
    assert batch_lookup_calls == 1


@pytest.mark.asyncio
async def test_auto_bom_backfill_dedupes_same_material_plant_candidates_in_sql(db_session):
    db_session.add_all([
        SalesPlanOrderLineSrc(
            sap_code="SAP-BOM-DEDUPE-001",
            sap_line_no="10",
            order_no="SO-DEDUPE-001",
            material_no="MAT-DEDUPE-001",
            delivery_plant="1100",
            drawing_released=True,
            confirmed_delivery_date=datetime(2026, 4, 6),
        ),
        SalesPlanOrderLineSrc(
            sap_code="SAP-BOM-DEDUPE-002",
            sap_line_no="20",
            order_no="SO-DEDUPE-002",
            material_no="MAT-DEDUPE-001",
            delivery_plant="1100",
            drawing_released=True,
            confirmed_delivery_date=datetime(2026, 4, 7),
        ),
        SalesPlanOrderLineSrc(
            sap_code="SAP-BOM-DEDUPE-003",
            sap_line_no="30",
            order_no="SO-DEDUPE-003",
            material_no="MAT-DEDUPE-001",
            delivery_plant="1100",
            drawing_released=True,
            confirmed_delivery_date=datetime(2026, 4, 8),
        ),
    ])
    await db_session.commit()

    service = AutoBomBackfillService(session_factory=_SessionFactory(db_session))
    result = await service.run(
        source="sales_plan_sync",
        reason="sales_plan_or_drawing_updated",
        sap_bom_base_url="https://sap.example.com",
    )

    queue_items = (
        await db_session.execute(select(BomBackfillQueue).where(BomBackfillQueue.material_no == "MAT-DEDUPE-001"))
    ).scalars().all()

    assert result.candidate_orders == 3
    assert result.candidate_items == 1
    assert result.enqueued_items == 1
    assert len(queue_items) == 1
    assert queue_items[0].plant == "1100"


@pytest.mark.asyncio
async def test_auto_bom_backfill_loads_candidates_with_single_sales_plan_query(db_session):
    db_session.add_all([
        SalesPlanOrderLineSrc(
            sap_code="SAP-BOM-QUERY-001",
            sap_line_no="10",
            order_no="SO-QUERY-001",
            material_no="MAT-QUERY-001",
            delivery_plant="1100",
            drawing_released=True,
            confirmed_delivery_date=datetime(2026, 4, 9),
        ),
        SalesPlanOrderLineSrc(
            sap_code="SAP-BOM-QUERY-002",
            sap_line_no="20",
            order_no="SO-QUERY-002",
            material_no="MAT-QUERY-001",
            delivery_plant="1100",
            drawing_released=True,
            confirmed_delivery_date=datetime(2026, 4, 10),
        ),
    ])
    await db_session.commit()

    sales_plan_query_count = 0

    @event.listens_for(db_session.bind.sync_engine, "before_cursor_execute")
    def _count_sales_plan_queries(conn, cursor, statement, parameters, context, executemany):
        nonlocal sales_plan_query_count
        normalized_statement = " ".join(statement.lower().split())
        if (
            normalized_statement.startswith("select")
            and "from sales_plan_order_line_src" in normalized_statement
            and "bom_relation_src" in normalized_statement
        ):
            sales_plan_query_count += 1

    try:
        service = AutoBomBackfillService(session_factory=_SessionFactory(db_session))
        result = await service.run(
            source="sales_plan_sync",
            reason="sales_plan_or_drawing_updated",
            sap_bom_base_url="https://sap.example.com",
        )
    finally:
        event.remove(db_session.bind.sync_engine, "before_cursor_execute", _count_sales_plan_queries)

    assert result.candidate_orders == 2
    assert result.candidate_items == 1
    assert sales_plan_query_count == 1


@pytest.mark.asyncio
async def test_auto_bom_backfill_distinguishes_existing_bom_by_plant(db_session):
    db_session.add_all([
        SalesPlanOrderLineSrc(
            sap_code="SAP-BOM-PLANT-001",
            sap_line_no="10",
            order_no="SO-PLANT-001",
            material_no="MAT-PLANT-001",
            delivery_plant="1100",
            drawing_released=True,
            confirmed_delivery_date=datetime(2026, 4, 9),
        ),
        SalesPlanOrderLineSrc(
            sap_code="SAP-BOM-PLANT-002",
            sap_line_no="20",
            order_no="SO-PLANT-002",
            material_no="MAT-PLANT-001",
            delivery_plant="1200",
            drawing_released=True,
            confirmed_delivery_date=datetime(2026, 4, 10),
        ),
    ])
    db_session.add(
        BomRelationSrc(
            machine_material_no="MAT-PLANT-001",
            plant="1100",
            material_no="MAT-PLANT-001",
            bom_component_no="COMP-PLANT-001",
        )
    )
    await db_session.commit()

    service = AutoBomBackfillService(session_factory=_SessionFactory(db_session))
    result = await service.run(
        source="sales_plan_sync",
        reason="sales_plan_or_drawing_updated",
        sap_bom_base_url="https://sap.example.com",
    )

    queue_items = (
        await db_session.execute(select(BomBackfillQueue).where(BomBackfillQueue.material_no == "MAT-PLANT-001"))
    ).scalars().all()

    assert result.candidate_orders == 1
    assert result.candidate_items == 1
    assert result.enqueued_items == 1
    assert len(queue_items) == 1
    assert queue_items[0].plant == "1200"


@pytest.mark.asyncio
async def test_auto_bom_backfill_consume_syncs_and_closes_issue(db_session, monkeypatch):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP-BOM-003",
        sap_line_no="30",
        order_no="SO-BOM-003",
        material_no="MAT-BOM-003",
        delivery_plant="1100",
        drawing_released=True,
        confirmed_delivery_date=datetime(2026, 4, 3),
    )
    issue = DataIssueRecord(
        issue_type="BOM缺失",
        issue_level="high",
        source_system="scheduler",
        biz_key="pending",
        issue_title="排产前缺少 BOM 数据",
        status="open",
    )
    db_session.add(order)
    await db_session.flush()
    issue.biz_key = str(order.id)
    db_session.add(issue)
    db_session.add(
        BomBackfillQueue(
            material_no="MAT-BOM-003",
            plant="1100",
            source="sales_plan_sync",
            trigger_reason="sales_plan_or_drawing_updated",
            status=BomBackfillQueueStatus.PENDING.value,
        )
    )
    await db_session.commit()

    monkeypatch.setattr(
        "app.integration.sap_bom_client.SapBomClient.fetch_bom",
        AsyncMock(return_value=[
            {
                "machine_material_no": "MAT-BOM-003",
                "machine_material_desc": "machine",
                "material_no": "MAT-BOM-003",
                "material_desc": "machine",
                "plant": "1100",
                "bom_component_no": "COMP-003",
                "bom_component_desc": "component",
                "part_type": "自产件",
                "component_qty": 1,
                "is_self_made": True,
            }
        ]),
    )

    service = AutoBomBackfillService(session_factory=_SessionFactory(db_session))
    result = await service.consume(
        source="scheduler_job",
        reason="bom_backfill_queue_consume",
        sap_bom_base_url="https://sap.example.com",
    )

    queue_item = (
        await db_session.execute(select(BomBackfillQueue).where(BomBackfillQueue.material_no == "MAT-BOM-003"))
    ).scalar_one()
    bom_rows = (
        await db_session.execute(select(BomRelationSrc).where(BomRelationSrc.machine_material_no == "MAT-BOM-003"))
    ).scalars().all()
    snapshot = (
        await db_session.execute(select(OrderScheduleSnapshot).where(OrderScheduleSnapshot.order_line_id == order.id))
    ).scalar_one_or_none()
    await db_session.refresh(issue)

    assert result.claimed_items == 1
    assert result.success_items == 1
    assert queue_item.status == BomBackfillQueueStatus.SUCCESS.value
    assert len(bom_rows) == 1
    assert snapshot is not None
    assert snapshot.schedule_status != "missing_bom"
    assert issue.status == "closed"


@pytest.mark.asyncio
async def test_auto_bom_backfill_consume_marks_retry_wait_on_transient_error(db_session, monkeypatch):
    db_session.add(
        BomBackfillQueue(
            material_no="MAT-BOM-004",
            plant="1100",
            source="sales_plan_sync",
            trigger_reason="sales_plan_or_drawing_updated",
            status=BomBackfillQueueStatus.PENDING.value,
        )
    )
    await db_session.commit()

    monkeypatch.setattr(
        "app.integration.sap_bom_client.SapBomClient.fetch_bom",
        AsyncMock(side_effect=httpx.ReadTimeout("timeout")),
    )

    service = AutoBomBackfillService(session_factory=_SessionFactory(db_session))
    result = await service.consume(
        source="scheduler_job",
        reason="bom_backfill_queue_consume",
        sap_bom_base_url="https://sap.example.com",
    )

    queue_item = (
        await db_session.execute(select(BomBackfillQueue).where(BomBackfillQueue.material_no == "MAT-BOM-004"))
    ).scalar_one()

    assert result.claimed_items == 1
    assert result.retry_wait_items == 1
    assert queue_item.status == BomBackfillQueueStatus.RETRY_WAIT.value
    assert queue_item.failure_kind == "transient_error"
    assert queue_item.next_retry_at is not None


@pytest.mark.asyncio
async def test_auto_bom_backfill_consume_uses_batch_queue_reload(db_session, monkeypatch):
    db_session.add_all([
        BomBackfillQueue(
            material_no="MAT-CONSUME-001",
            plant="1100",
            source="sales_plan_sync",
            trigger_reason="sales_plan_or_drawing_updated",
            status=BomBackfillQueueStatus.PENDING.value,
        ),
        BomBackfillQueue(
            material_no="MAT-CONSUME-002",
            plant="1100",
            source="sales_plan_sync",
            trigger_reason="sales_plan_or_drawing_updated",
            status=BomBackfillQueueStatus.PENDING.value,
        ),
    ])
    await db_session.commit()

    original_find_by_ids = BomBackfillQueueRepo.find_by_ids

    async def fail_single_lookup(self, item_id):
        raise AssertionError("consume_queue should not reload queue items one by one")

    batch_lookup_calls = 0

    async def track_find_by_ids(self, ids):
        nonlocal batch_lookup_calls
        batch_lookup_calls += 1
        return await original_find_by_ids(self, ids)

    monkeypatch.setattr(
        "app.integration.sap_bom_client.SapBomClient.fetch_bom",
        AsyncMock(side_effect=[
            httpx.ReadTimeout("timeout"),
            httpx.ReadTimeout("timeout"),
        ]),
    )
    monkeypatch.setattr(BomBackfillQueueRepo, "get_by_id", fail_single_lookup)
    monkeypatch.setattr(BomBackfillQueueRepo, "find_by_ids", track_find_by_ids)

    service = AutoBomBackfillService(session_factory=_SessionFactory(db_session))
    result = await service.consume(
        source="scheduler_job",
        reason="bom_backfill_queue_consume",
        sap_bom_base_url="https://sap.example.com",
    )

    assert result.claimed_items == 2
    assert result.retry_wait_items == 2
    assert batch_lookup_calls == 1


@pytest.mark.asyncio
async def test_auto_bom_backfill_consume_finishes_existing_sync_job_when_queue_is_empty(db_session):
    job = SyncJobLog(
        job_type="bom_backfill_queue",
        source_system="system",
        start_time=datetime.now(),
        heartbeat_at=datetime.now(),
        status="running",
        timeout_seconds=7200,
        message="调度触发 BOM 补数队列消费，任务已进入后台队列。",
    )
    db_session.add(job)
    await db_session.commit()

    service = AutoBomBackfillService(session_factory=_SessionFactory(db_session))
    result = await service.consume(
        source="scheduler_job",
        reason="bom_backfill_queue_consume",
        sap_bom_base_url="https://sap.example.com",
        existing_job_id=job.id,
    )

    await db_session.refresh(job)

    assert result.job_id == job.id
    assert result.claimed_items == 0
    assert "当前没有待消费的 BOM 补数队列项" in result.message
    assert job.status == "completed"
    assert job.end_time is not None
    assert job.fail_count == 0
    assert "当前没有待消费的 BOM 补数队列项" in (job.message or "")
