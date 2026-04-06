from datetime import datetime
from types import SimpleNamespace

import pytest

from app.common.enums import BomBackfillQueueStatus
from app.models.bom_backfill_queue import BomBackfillQueue
from app.models.bom_relation import BomRelationSrc
from app.models.data_issue import DataIssueRecord
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sync_job_log import SyncJobLog


class _FakeManualSyncService:
    def __init__(self, *, job_id: int = 1, created: bool = True):
        self.job = SimpleNamespace(id=job_id, status="queued")
        self.created = created
        self.sales_plan_dispatches: list[dict | None] = []
        self.bom_dispatches: list[list[tuple[str, str]]] = []
        self.research_dispatches: list[str | None] = []

    async def enqueue_sales_plan(self, session, **kwargs):
        self.last_create_job_kwargs = kwargs
        if self.created:
            self.sales_plan_dispatches.append(kwargs.get("filter_payload"))
        return self.job.id, self.job.status, self.created

    async def enqueue_bom(self, session, **kwargs):
        self.last_create_job_kwargs = kwargs
        if self.created:
            self.bom_dispatches.append(kwargs.get("items"))
        return self.job.id, self.job.status, self.created

    async def enqueue_production_orders(self, session, **kwargs):
        self.last_create_job_kwargs = kwargs
        return self.job.id, self.job.status, self.created

    async def enqueue_research(self, session, **kwargs):
        self.last_create_job_kwargs = kwargs
        if self.created:
            self.research_dispatches.append(kwargs.get("order_no_filter"))
        return self.job.id, self.job.status, self.created


class _FakeSyncSchedulerControlService:
    def __init__(self):
        self.enabled = False

    async def get_status(self) -> dict:
        return {
            "enabled": self.enabled,
            "state": "running" if self.enabled else "paused",
            "timezone": "Asia/Shanghai",
            "jobs": [{"id": "sales_plan_sync", "name": "sales_plan_sync", "next_run_time": None}],
        }

    async def set_enabled(self, enabled: bool | None, *, updated_by: str) -> dict:
        if enabled is not None:
            self.enabled = enabled
        return await self.get_status()


@pytest.mark.asyncio
async def test_admin_api_requires_token(app_client_no_admin_token):
    resp = await app_client_no_admin_token.get("/api/admin/sync/schedule")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "User session is invalid or expired."


@pytest.mark.asyncio
async def test_sync_sales_plan_trigger_returns_job_and_dispatches(app_client, monkeypatch):
    service = _FakeManualSyncService(job_id=101, created=True)
    monkeypatch.setattr("app.routers.admin_sync_router._get_manual_sync_service", lambda: service)
    monkeypatch.setattr(
        "app.routers.admin_sync_router.build_sales_plan_filter_window",
        lambda **kwargs: SimpleNamespace(
            filter_payload={
                "combineType": "AND",
                "conditions": [
                    {
                        "type": "condition",
                        "value": {"name": "订单明细-确认交货期", "filterType": "NOT_NULL"},
                    }
                ],
            },
        ),
    )
    monkeypatch.setattr(
        "app.routers.admin_sync_router.format_sales_plan_filter_window",
        lambda window: "确认交货期非空",
    )

    resp = await app_client.post(
        "/api/admin/sync/sales-plan",
        json={"start_time": None, "end_time": None},
    )

    body = resp.json()

    assert body["code"] == 0
    assert body["data"] == {
        "job_id": 101,
        "status": "queued",
        "message": "销售计划手动同步已触发，请稍后查看同步日志。",
    }
    assert service.sales_plan_dispatches == [
        {
            "combineType": "AND",
            "conditions": [
                {
                    "type": "condition",
                    "value": {"name": "订单明细-确认交货期", "filterType": "NOT_NULL"},
                }
            ],
        }
    ]
    assert service.last_create_job_kwargs["operator_name"] == "系统管理员"


@pytest.mark.asyncio
async def test_sync_sales_plan_invalid_window_returns_validation_error(app_client, monkeypatch):
    service = _FakeManualSyncService(job_id=101, created=True)
    monkeypatch.setattr("app.routers.admin_sync_router._get_manual_sync_service", lambda: service)
    monkeypatch.setattr(
        "app.routers.admin_sync_router.build_sales_plan_filter_window",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("销售计划同步时间窗口无效：start_time 必须早于 end_time。")),
    )

    resp = await app_client.post(
        "/api/admin/sync/sales-plan",
        json={"start_time": "2026-03-21T10:00:00", "end_time": "2026-03-20T10:00:00"},
    )
    body = resp.json()

    assert body["code"] == 4003
    assert body["message"] == "销售计划同步时间窗口无效：start_time 必须早于 end_time。"


@pytest.mark.asyncio
async def test_sync_research_returns_existing_job_without_redispatch(app_client, monkeypatch):
    service = _FakeManualSyncService(job_id=202, created=False)
    monkeypatch.setattr("app.routers.admin_sync_router._get_manual_sync_service", lambda: service)

    resp = await app_client.post(
        "/api/admin/sync/research",
        json={"mode": "by_order_no", "order_no": "SO-001"},
    )

    body = resp.json()

    assert body["code"] == 0
    assert body["data"] == {
        "job_id": 202,
        "status": "queued",
        "message": "研究所数据同步任务已在运行中，请查看当前任务日志。",
    }
    assert service.research_dispatches == []


@pytest.mark.asyncio
async def test_sync_bom_with_order_line_ids_uses_batch_lookup(app_client, monkeypatch):
    service = _FakeManualSyncService(job_id=303, created=True)

    class _FakeOrder:
        def __init__(self, material_no: str, delivery_plant: str | None):
            self.material_no = material_no
            self.delivery_plant = delivery_plant

    captured_ids: list[int] = []

    async def fake_find_by_ids(self, ids):
        captured_ids.extend(ids)
        return [
            _FakeOrder("MAT-BATCH-001", "1100"),
            _FakeOrder("MAT-BATCH-002", None),
        ]

    async def fail_get_by_id(self, _id):
        raise AssertionError("sync_bom should not query sales orders one by one")

    monkeypatch.setattr("app.routers.admin_sync_router._get_manual_sync_service", lambda: service)
    monkeypatch.setattr("app.repository.sales_plan_repo.SalesPlanRepo.find_by_ids", fake_find_by_ids)
    monkeypatch.setattr("app.repository.sales_plan_repo.SalesPlanRepo.get_by_id", fail_get_by_id)

    resp = await app_client.post(
        "/api/admin/sync/bom",
        json={"order_line_ids": [11, 12]},
    )
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["job_id"] == 303
    assert captured_ids == [11, 12]
    assert service.last_create_job_kwargs["operator_name"] == "系统管理员"
    assert service.bom_dispatches == [[("MAT-BATCH-001", "1100"), ("MAT-BATCH-002", "1000")]]


@pytest.mark.asyncio
async def test_get_sync_schedule_status(app_client, monkeypatch):
    scheduler = _FakeSyncSchedulerControlService()
    monkeypatch.setattr("app.routers.admin_sync_router.SyncSchedulerControlService", lambda session: scheduler)

    resp = await app_client.get("/api/admin/sync/schedule")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["enabled"] is False
    assert body["data"]["state"] == "paused"
    assert len(body["data"]["jobs"]) == 1


@pytest.mark.asyncio
async def test_control_sync_schedule_enable_and_disable(app_client, monkeypatch):
    scheduler = _FakeSyncSchedulerControlService()
    monkeypatch.setattr("app.routers.admin_sync_router.SyncSchedulerControlService", lambda session: scheduler)

    enable_resp = await app_client.post("/api/admin/sync/schedule", json={"enabled": True})
    enable_body = enable_resp.json()
    assert enable_body["code"] == 0
    assert enable_body["data"]["enabled"] is True
    assert enable_body["data"]["state"] == "running"

    disable_resp = await app_client.post("/api/admin/sync/schedule", json={"enabled": False})
    disable_body = disable_resp.json()
    assert disable_body["code"] == 0
    assert disable_body["data"]["enabled"] is False
    assert disable_body["data"]["state"] == "paused"


@pytest.mark.asyncio
async def test_delete_sync_log_not_found_returns_not_found_code(app_client):
    delete_resp = await app_client.delete("/api/admin/sync-logs/999999")
    delete_body = delete_resp.json()

    assert delete_body["code"] == 4002
    assert delete_body["message"] == "记录不存在"


@pytest.mark.asyncio
async def test_get_sync_observability_summary(app_client, db_session):
    db_session.add_all(
        [
            OrderScheduleSnapshot(order_line_id=1, schedule_status="missing_bom", drawing_released=True),
            OrderScheduleSnapshot(order_line_id=2, schedule_status="pending_drawing", drawing_released=False),
            BomBackfillQueue(
                material_no="MAT-Q-001",
                plant="1100",
                source="sales_plan_sync",
                trigger_reason="sales_plan_or_drawing_updated",
                status=BomBackfillQueueStatus.PENDING.value,
            ),
            BomBackfillQueue(
                material_no="MAT-Q-002",
                plant="1100",
                source="sales_plan_sync",
                trigger_reason="sales_plan_or_drawing_updated",
                status=BomBackfillQueueStatus.RETRY_WAIT.value,
                failure_kind="transient_error",
                fail_count=2,
            ),
            BomRelationSrc(machine_material_no="MAT-001", bom_component_no="COMP-1"),
            BomRelationSrc(machine_material_no="MAT-002", bom_component_no="COMP-2"),
            DataIssueRecord(
                issue_type="BOM缺失",
                issue_title="缺少BOM",
                status="open",
                source_system="scheduler",
                biz_key="1",
            ),
            SyncJobLog(
                job_type="sales_plan",
                source_system="guandata",
                start_time=datetime.now(),
                status="completed",
                success_count=12,
                fail_count=0,
                message="销售计划同步完成：成功 12 条，失败 0 条，发图状态回填 3 条，自动补 BOM 候选 5 个。",
            ),
            SyncJobLog(
                job_type="bom",
                source_system="sap",
                start_time=datetime.now(),
                status="running",
                success_count=10,
                fail_count=1,
                message="自动补齐 BOM 执行中：第 2/4 批；本轮处理 20 个；已成功 10 条；已失败 1 条；待后续继续 60 个。",
            ),
        ]
    )
    await db_session.commit()

    resp = await app_client.get("/api/admin/sync/observability")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["snapshot_total"] == 2
    assert body["data"]["missing_bom_snapshot_count"] == 1
    assert body["data"]["open_missing_bom_issue_count"] == 1
    assert body["data"]["distinct_machine_bom_count"] == 2
    assert body["data"]["running_job_count"] == 1
    assert body["data"]["bom_backfill_queue"]["pending"] == 1
    assert body["data"]["bom_backfill_queue"]["retry_wait"] == 1
    assert body["data"]["bom_backfill_queue"]["failure_kind_counts"]["transient_error"] == 1
    assert body["data"]["latest_sales_plan_job"]["progress"]["drawing_updated_count"] == 3
    assert body["data"]["latest_auto_bom_job"]["progress"]["batch_current"] == 2
    assert body["data"]["latest_auto_bom_job"]["progress"]["deferred_items"] == 60


@pytest.mark.asyncio
async def test_get_sync_observability_summary_uses_aggregated_queue_stats(app_client, db_session, monkeypatch):
    db_session.add(
        BomBackfillQueue(
            material_no="MAT-Q-AGG-001",
            plant="1100",
            source="sales_plan_sync",
            trigger_reason="sales_plan_or_drawing_updated",
            status=BomBackfillQueueStatus.PENDING.value,
        )
    )
    await db_session.commit()

    async def fail_count_by_status(self):
        raise AssertionError("count_by_status should not be used by observability summary")

    async def fail_count_retry_wait_due(self):
        raise AssertionError("count_retry_wait_due should not be used by observability summary")

    async def fail_count_failure_kind(self):
        raise AssertionError("count_failure_kind should not be used by observability summary")

    async def fail_get_oldest_pending(self):
        raise AssertionError("get_oldest_pending should not be used by observability summary")

    async def fail_list_recent_failed(self, limit: int = 5):
        raise AssertionError("list_recent_failed should not be used by observability summary")

    monkeypatch.setattr(
        "app.repository.bom_backfill_queue_repo.BomBackfillQueueRepo.count_by_status", fail_count_by_status
    )
    monkeypatch.setattr(
        "app.repository.bom_backfill_queue_repo.BomBackfillQueueRepo.count_retry_wait_due",
        fail_count_retry_wait_due,
    )
    monkeypatch.setattr(
        "app.repository.bom_backfill_queue_repo.BomBackfillQueueRepo.count_failure_kind",
        fail_count_failure_kind,
    )
    monkeypatch.setattr(
        "app.repository.bom_backfill_queue_repo.BomBackfillQueueRepo.get_oldest_pending",
        fail_get_oldest_pending,
    )
    monkeypatch.setattr(
        "app.repository.bom_backfill_queue_repo.BomBackfillQueueRepo.list_recent_failed",
        fail_list_recent_failed,
    )

    resp = await app_client.get("/api/admin/sync/observability")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["bom_backfill_queue"]["pending"] == 1


@pytest.mark.asyncio
async def test_get_sync_observability_summary_uses_aggregated_latest_job_lookup(app_client, db_session, monkeypatch):
    sales_plan_job = SyncJobLog(
        job_type="sales_plan",
        source_system="guandata",
        start_time=datetime.now(),
        status="completed",
        success_count=3,
        fail_count=0,
        message="销售计划同步完成：成功 3 条，失败 0 条。",
    )
    auto_bom_job = SyncJobLog(
        job_type="bom",
        source_system="sap",
        start_time=datetime.now(),
        status="completed",
        success_count=2,
        fail_count=0,
        message="自动补齐 BOM 完成：成功 2 条，失败 0 条。",
    )
    db_session.add_all([sales_plan_job, auto_bom_job])
    await db_session.commit()

    async def fail_get_latest_job(self, *, job_type: str):
        raise AssertionError(f"_get_latest_job should not be used for {job_type}")

    async def fail_get_latest_auto_bom_job(self):
        raise AssertionError("_get_latest_auto_bom_job should not be used")

    monkeypatch.setattr(
        "app.services.sync_job_observability_service.SyncJobObservabilityService._get_latest_job",
        fail_get_latest_job,
    )
    monkeypatch.setattr(
        "app.services.sync_job_observability_service.SyncJobObservabilityService._get_latest_auto_bom_job",
        fail_get_latest_auto_bom_job,
    )

    resp = await app_client.get("/api/admin/sync/observability")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["latest_sales_plan_job"]["id"] == sales_plan_job.id
    assert body["data"]["latest_auto_bom_job"]["id"] == auto_bom_job.id


@pytest.mark.asyncio
async def test_get_sync_log_returns_structured_progress(app_client, db_session):
    entity = SyncJobLog(
        job_type="bom",
        source_system="sap",
        start_time=datetime.now(),
        status="completed",
        success_count=20,
        fail_count=0,
        message="自动补齐 BOM 完成：候选订单 30 条；候选物料 20 个；本轮处理 20 个；递延 0 个；成功 20 条；失败 0 条；刷新快照 18 条；收口缺 BOM 异常 4 条。",
    )
    db_session.add(entity)
    await db_session.commit()

    resp = await app_client.get(f"/api/admin/sync-logs/{entity.id}")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["progress"]["kind"] == "auto_bom_backfill"
    assert body["data"]["progress"]["candidate_orders"] == 30
    assert body["data"]["progress"]["refreshed_order_count"] == 18


@pytest.mark.asyncio
async def test_list_sync_logs_supports_sort_by_message(app_client, db_session):
    db_session.add_all(
        [
            SyncJobLog(
                job_type="sales_plan",
                source_system="guandata",
                start_time=datetime(2026, 3, 21, 9, 0, 0),
                status="completed",
                success_count=1,
                fail_count=0,
                message="zeta message",
            ),
            SyncJobLog(
                job_type="sales_plan",
                source_system="guandata",
                start_time=datetime(2026, 3, 21, 10, 0, 0),
                status="completed",
                success_count=1,
                fail_count=0,
                message="alpha message",
            ),
        ]
    )
    await db_session.commit()

    resp = await app_client.get("/api/admin/sync-logs?sort_field=message&sort_order=asc&page_size=20")
    body = resp.json()

    assert body["code"] == 0
    items = [item for item in body["data"]["items"] if item["message"] in {"alpha message", "zeta message"}]
    assert [item["message"] for item in items] == ["alpha message", "zeta message"]


@pytest.mark.asyncio
async def test_list_and_retry_bom_backfill_queue(app_client, db_session):
    first = BomBackfillQueue(
        material_no="MAT-R-001",
        plant="1100",
        source="sales_plan_sync",
        trigger_reason="sales_plan_or_drawing_updated",
        status=BomBackfillQueueStatus.FAILED.value,
        fail_count=5,
        failure_kind="permanent_error",
    )
    second = BomBackfillQueue(
        material_no="MAT-R-002",
        plant="1100",
        source="research_sync",
        trigger_reason="drawing_status_backfill",
        status=BomBackfillQueueStatus.RETRY_WAIT.value,
        fail_count=2,
        failure_kind="transient_error",
    )
    db_session.add_all([first, second])
    await db_session.commit()

    list_resp = await app_client.get("/api/admin/sync/bom-backfill-queue", params={"status": "failed"})
    list_body = list_resp.json()
    assert list_body["code"] == 0
    assert list_body["data"]["total"] == 1
    assert list_body["data"]["items"][0]["material_no"] == "MAT-R-001"

    retry_resp = await app_client.post(
        "/api/admin/sync/bom-backfill-queue/retry",
        json={"ids": [first.id, second.id]},
    )
    retry_body = retry_resp.json()
    assert retry_body["code"] == 0
    assert retry_body["data"]["updated_count"] == 2

    await db_session.refresh(first)
    await db_session.refresh(second)
    assert first.status == BomBackfillQueueStatus.PENDING.value
    assert second.status == BomBackfillQueueStatus.PENDING.value
