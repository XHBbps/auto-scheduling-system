from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.sync.auto_bom_backfill_service import AutoBomBackfillResult
from app.sync.sync_support_utils import SyncResult
from app.sync.sync_workflow_service import SyncWorkflowService


@pytest.mark.asyncio
async def test_sync_sales_plan_triggers_auto_bom_for_touched_and_drawing_updated_orders(
    db_session,
    monkeypatch,
):
    class _FakeSalesPlanSyncService:
        def __init__(self, session, client):
            self.session = session
            self.client = client

        async def sync(self, filters=None, job=None):
            return SyncResult(success_count=2, insert_count=2)

        def get_touched_order_line_ids(self):
            return [5, 6]

    auto_bom_mock = AsyncMock(return_value=AutoBomBackfillResult(candidate_orders=3, candidate_items=2, created=True))
    refresh_batch_mock = AsyncMock(
        return_value={"total": 1, "refreshed": 1, "scheduled": 0, "scheduled_stale": 0, "deleted": 0}
    )

    monkeypatch.setattr("app.sync.sync_workflow_service.SalesPlanSyncService", _FakeSalesPlanSyncService)
    monkeypatch.setattr(settings, "sap_bom_base_url", "https://sap.example.com")
    monkeypatch.setattr(
        "app.sync.sync_workflow_service.DrawingStatusSyncService.refresh_all_with_ids",
        AsyncMock(return_value=[6, 7]),
    )
    monkeypatch.setattr(
        "app.sync.sync_workflow_service.AutoBomBackfillService.run",
        auto_bom_mock,
    )
    monkeypatch.setattr(
        "app.sync.sync_workflow_service.ScheduleSnapshotRefreshService.refresh_batch",
        refresh_batch_mock,
    )

    workflow = SyncWorkflowService(db_session)
    result = await workflow.sync_sales_plan(client=object())

    assert result.sync_result.success_count == 2
    assert result.drawing_updated_count == 2
    assert result.auto_bom_backfill is not None
    auto_bom_mock.assert_awaited_once()
    kwargs = auto_bom_mock.await_args.kwargs
    assert kwargs["source"] == "sales_plan_sync"
    assert kwargs["reason"] == "sales_plan_or_drawing_updated"
    assert kwargs["order_line_ids"] == [5, 6, 7]
