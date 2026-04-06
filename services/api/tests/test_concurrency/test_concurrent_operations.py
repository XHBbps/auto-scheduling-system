"""Concurrency safety tests for critical operations.

These tests validate that concurrent operations don't corrupt data.
They use SQLite which lacks PostgreSQL advisory locks and skip_locked,
so they focus on application-level concurrency safety (savepoints,
state checks, deduplication).
"""

import pytest
from sqlalchemy import select

from app.common.datetime_utils import utc_now
from app.common.enums import BackgroundTaskStatus
from app.models.background_task import BackgroundTask
from app.models.bom_relation import BomRelationSrc
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc


@pytest.mark.asyncio
async def test_bom_sync_savepoint_preserves_data_on_insert_failure(db_session, monkeypatch):
    """When BOM insert fails after delete, the savepoint rolls back the
    delete so existing BOM data is preserved."""
    from app.sync.bom_sync_service import BomSyncService

    # Seed existing BOM data that must survive
    existing = BomRelationSrc(
        machine_material_no="MAT-001",
        plant="1000",
        material_no="MAT-001",
        bom_component_no="COMP-001",
        bom_level=1,
        is_top_level=True,
        is_self_made=False,
        sync_time=utc_now(),
    )
    db_session.add(existing)
    await db_session.commit()

    # Create a mock SAP client that returns valid data
    class FakeSapClient:
        async def fetch_bom(self, material_no, plant):
            return [
                {
                    "machine_material_no": material_no,
                    "material_no": material_no,
                    "bom_component_no": "COMP-NEW",
                    "part_type": "test",
                }
            ]

    service = BomSyncService(db_session, FakeSapClient())

    # Monkeypatch repo.add_all to raise an exception AFTER delete succeeds
    _original_add_all = service.repo.add_all

    async def failing_add_all(entities):
        raise RuntimeError("Simulated insert failure")

    monkeypatch.setattr(service.repo, "add_all", failing_add_all)

    result = await service.sync_item("MAT-001", "1000")

    # Sync should report failure
    assert not result.success
    assert result.error_kind == "replace_failed"

    # The original BOM data must still exist (savepoint rolled back the delete)
    rows = (
        (await db_session.execute(select(BomRelationSrc).where(BomRelationSrc.machine_material_no == "MAT-001")))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].bom_component_no == "COMP-001"


@pytest.mark.asyncio
async def test_concurrent_task_claim_no_double_execution(db_session):
    """Two workers claiming tasks concurrently should not claim the same task.

    Note: SQLite doesn't support skip_locked, so this test validates the
    application logic of status transitions rather than DB-level locking.
    """
    from app.repository.background_task_repo import BackgroundTaskRepo

    # Create a single pending task
    task = BackgroundTask(
        task_type="sales_plan_sync",
        status=BackgroundTaskStatus.PENDING.value,
        source="test",
        payload={},
        attempt_count=0,
        max_attempts=3,
        available_at=utc_now(),
    )
    db_session.add(task)
    await db_session.commit()

    repo = BackgroundTaskRepo(db_session)

    # First claim should succeed
    claimed_1 = await repo.claim_available(worker_id="worker-A", limit=1)
    await db_session.commit()
    assert len(claimed_1) == 1
    assert claimed_1[0].worker_id == "worker-A"
    assert claimed_1[0].status == BackgroundTaskStatus.RUNNING.value

    # Second claim should find nothing (task already RUNNING)
    claimed_2 = await repo.claim_available(worker_id="worker-B", limit=1)
    assert len(claimed_2) == 0


@pytest.mark.asyncio
async def test_concurrent_snapshot_refresh_produces_consistent_state(db_session):
    """Two snapshot refreshes for the same order should both produce
    a valid final state without data corruption."""
    from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService

    # Seed a sales plan order
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001",
        sap_line_no="10",
        material_no="MAT-001",
        product_model="MODEL-A",
        confirmed_delivery_date=utc_now(),
    )
    db_session.add(order)
    await db_session.flush()

    service = ScheduleSnapshotRefreshService(db_session)

    # Run refresh twice sequentially (simulating concurrent scenario)
    await service.refresh_one(
        order_line_id=order.id,
        source="test_1",
        reason="concurrent_test_1",
    )
    await db_session.flush()

    await service.refresh_one(
        order_line_id=order.id,
        source="test_2",
        reason="concurrent_test_2",
    )
    await db_session.flush()

    # Verify exactly one snapshot exists with the latest refresh source
    snapshots = (
        (await db_session.execute(select(OrderScheduleSnapshot).where(OrderScheduleSnapshot.order_line_id == order.id)))
        .scalars()
        .all()
    )

    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.last_refresh_source == "test_2"
    assert snapshot.refresh_reason == "concurrent_test_2"
    assert snapshot.order_line_id == order.id
