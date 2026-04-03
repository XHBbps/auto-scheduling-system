import asyncio
import logging
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.datetime_utils import utc_now
from app.common.enums import BackgroundTaskStatus
from app.common.exceptions import BizException, ErrorCode
from app.models.background_task import BackgroundTask
from app.models.sync_job_log import SyncJobLog
from app.services.background_task_worker_service import BackgroundTaskWorkerService
from app.sync.sync_support_utils import SyncResult


@pytest.mark.asyncio
async def test_execute_task_failure_keeps_handler_committed_changes(db_session, monkeypatch):
    task = BackgroundTask(
        task_type='sales_plan_sync',
        status=BackgroundTaskStatus.RUNNING.value,
        source='test',
        reason='queued',
        payload={'filter_payload': {'k': 'v'}},
        attempt_count=1,
        max_attempts=1,
        available_at=utc_now(),
        claimed_at=utc_now(),
        started_at=utc_now(),
        worker_id='worker-test',
    )
    db_session.add(task)
    await db_session.commit()

    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    worker = BackgroundTaskWorkerService(session_factory=session_factory)

    async def fake_heartbeat_loop(task_id: int) -> None:
        return None

    async def fail_after_commit(session, task_context, payload):
        task_in_handler = await session.get(BackgroundTask, task_context.task_id)
        task_in_handler.reason = 'handler_committed'
        await session.commit()
        raise RuntimeError('boom after handler commit')

    monkeypatch.setattr(worker, '_heartbeat_loop', fake_heartbeat_loop)
    monkeypatch.setattr(worker, '_execute_sales_plan', fail_after_commit)

    await worker.execute_task(task.id)

    await db_session.refresh(task)
    assert task.status == BackgroundTaskStatus.FAILED.value
    assert task.reason == 'handler_committed'
    assert task.last_error is not None
    assert 'failure_kind=unexpected_error' in task.last_error
    assert 'task_type=sales_plan_sync' in task.last_error
    assert 'error=boom after handler commit' in task.last_error


@pytest.mark.asyncio
async def test_execute_task_failure_logs_failure_kind_and_stage(db_session, monkeypatch, caplog):
    task = BackgroundTask(
        task_type='sales_plan_sync',
        status=BackgroundTaskStatus.RUNNING.value,
        source='test',
        reason='queued',
        payload={'filter_payload': {'k': 'v'}},
        attempt_count=1,
        max_attempts=1,
        available_at=utc_now(),
        claimed_at=utc_now(),
        started_at=utc_now(),
        worker_id='worker-test',
    )
    db_session.add(task)
    await db_session.commit()

    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    worker = BackgroundTaskWorkerService(session_factory=session_factory)

    async def fake_heartbeat_loop(task_id: int) -> None:
        return None

    async def fail_with_biz_exception(session, task_context, payload):
        raise BizException(ErrorCode.EXPORT_FAILED, 'export exploded')

    monkeypatch.setattr(worker, '_heartbeat_loop', fake_heartbeat_loop)
    monkeypatch.setattr(worker, '_execute_sales_plan', fail_with_biz_exception)

    with caplog.at_level(logging.INFO):
        await worker.execute_task(task.id)

    await db_session.refresh(task)
    assert task.last_error is not None
    assert 'failure_kind=export_failed' in task.last_error
    assert 'stage=execute_task' in task.last_error
    assert 'error=export exploded' in task.last_error
    assert 'Background task execution failed' in caplog.text
    assert 'failure_kind=export_failed' in caplog.text


@pytest.mark.asyncio
async def test_execute_production_order_task_enqueues_part_cycle_rebuild(db_session, monkeypatch):
    task = BackgroundTask(
        task_type='production_order_sync',
        status=BackgroundTaskStatus.RUNNING.value,
        source='test',
        reason='queued',
        payload={},
        attempt_count=1,
        max_attempts=1,
        available_at=utc_now(),
        claimed_at=utc_now(),
        started_at=utc_now(),
        worker_id='worker-test',
    )
    db_session.add(task)
    await db_session.commit()

    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    worker = BackgroundTaskWorkerService(session_factory=session_factory)

    async def fake_heartbeat_loop(task_id: int) -> None:
        return None

    async def fake_sync(self, last_sync_ms=None, job=None):
        result = SyncResult()
        result.record_insert()
        return result

    monkeypatch.setattr(worker, '_heartbeat_loop', fake_heartbeat_loop)
    monkeypatch.setattr('app.sync.production_order_sync_service.ProductionOrderSyncService.sync', fake_sync)

    await worker.execute_task(task.id)

    pending_rebuild = (
        await db_session.execute(
            select(BackgroundTask).where(BackgroundTask.task_type == 'part_cycle_baseline_rebuild')
        )
    ).scalars().all()

    await db_session.refresh(task)
    assert task.status == BackgroundTaskStatus.SUCCEEDED.value
    assert len(pending_rebuild) == 1
    assert pending_rebuild[0].status == BackgroundTaskStatus.PENDING.value
    assert pending_rebuild[0].dedupe_key == 'baseline_rebuild:part_cycle'


@pytest.mark.asyncio
async def test_execute_part_cycle_baseline_rebuild_finishes_linked_sync_job(db_session, monkeypatch):
    job = SyncJobLog(
        job_type='part_cycle_baseline',
        source_system='system',
        start_time=utc_now(),
        heartbeat_at=utc_now(),
        status='running',
        timeout_seconds=7200,
        message='queued',
    )
    db_session.add(job)
    await db_session.flush()

    task = BackgroundTask(
        task_type='part_cycle_baseline_rebuild',
        status=BackgroundTaskStatus.RUNNING.value,
        source='test',
        reason='queued',
        payload={},
        sync_job_log_id=job.id,
        attempt_count=1,
        max_attempts=1,
        available_at=utc_now(),
        claimed_at=utc_now(),
        started_at=utc_now(),
        worker_id='worker-test',
    )
    db_session.add(task)
    await db_session.commit()

    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    worker = BackgroundTaskWorkerService(session_factory=session_factory)

    async def fake_heartbeat_loop(task_id: int) -> None:
        return None

    async def fake_rebuild(self, **kwargs):
        return {
            'eligible_groups': 8,
            'promoted_groups': 8,
            'persisted_groups': 0,
            'manual_protected_groups': 0,
            'deactivated_groups': 0,
            'snapshot_refresh': {'refreshed': 0},
        }

    monkeypatch.setattr(worker, '_heartbeat_loop', fake_heartbeat_loop)
    monkeypatch.setattr('app.baseline.part_cycle_baseline_service.PartCycleBaselineService.rebuild', fake_rebuild)

    await worker.execute_task(task.id)

    await db_session.refresh(task)
    await db_session.refresh(job)
    assert task.status == BackgroundTaskStatus.SUCCEEDED.value
    assert job.status == 'completed'
    assert job.end_time is not None
    assert job.heartbeat_at is not None
    assert job.success_count == 1
    assert '零件周期基准重建完成' in (job.message or '')


@pytest.mark.asyncio
async def test_execute_snapshot_reconcile_finishes_linked_sync_job(db_session, monkeypatch):
    job = SyncJobLog(
        job_type='schedule_snapshot_reconcile',
        source_system='system',
        start_time=utc_now(),
        heartbeat_at=utc_now(),
        status='running',
        timeout_seconds=7200,
        message='queued',
    )
    db_session.add(job)
    await db_session.flush()

    task = BackgroundTask(
        task_type='schedule_snapshot_reconcile',
        status=BackgroundTaskStatus.RUNNING.value,
        source='scheduler_job',
        reason='schedule_snapshot_reconcile',
        payload={},
        sync_job_log_id=job.id,
        attempt_count=1,
        max_attempts=1,
        available_at=utc_now(),
        claimed_at=utc_now(),
        started_at=utc_now(),
        worker_id='worker-test',
    )
    db_session.add(task)
    await db_session.commit()

    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    worker = BackgroundTaskWorkerService(session_factory=session_factory)

    async def fake_heartbeat_loop(task_id: int) -> None:
        return None

    async def fake_rebuild_all_open_snapshots(self, **kwargs):
        return {
            'total': 12,
            'refreshed': 7,
            'scheduled': 4,
            'scheduled_stale': 2,
            'deleted': 1,
        }

    monkeypatch.setattr(worker, '_heartbeat_loop', fake_heartbeat_loop)
    monkeypatch.setattr('app.services.schedule_snapshot_refresh_service.ScheduleSnapshotRefreshService.rebuild_all_open_snapshots', fake_rebuild_all_open_snapshots)

    await worker.execute_task(task.id)

    await db_session.refresh(task)
    await db_session.refresh(job)
    assert task.status == BackgroundTaskStatus.SUCCEEDED.value
    assert job.status == 'completed'
    assert job.success_count == 7
    assert '快照对账完成' in (job.message or '')


@pytest.mark.asyncio
async def test_execute_bom_backfill_queue_consume_finishes_linked_sync_job(db_session, monkeypatch):
    job = SyncJobLog(
        job_type='bom_backfill_queue',
        source_system='system',
        start_time=utc_now(),
        heartbeat_at=utc_now(),
        status='running',
        timeout_seconds=7200,
        message='queued',
    )
    db_session.add(job)
    await db_session.flush()

    task = BackgroundTask(
        task_type='bom_backfill_queue_consume',
        status=BackgroundTaskStatus.RUNNING.value,
        source='scheduler_job',
        reason='bom_backfill_queue_consume',
        payload={},
        sync_job_log_id=job.id,
        attempt_count=1,
        max_attempts=1,
        available_at=utc_now(),
        claimed_at=utc_now(),
        started_at=utc_now(),
        worker_id='worker-test',
    )
    db_session.add(task)
    await db_session.commit()

    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    worker = BackgroundTaskWorkerService(session_factory=session_factory)

    async def fake_heartbeat_loop(task_id: int) -> None:
        return None

    async def fake_consume(self, **kwargs):
        return SimpleNamespace(
            job_id=job.id,
            claimed_items=0,
            processed_items=0,
            success_items=0,
            retry_wait_items=0,
            failed_items=0,
            total_success_rows=0,
            total_fail_rows=0,
            message='scheduler_job:bom_backfill_queue_consume 当前没有待消费的 BOM 补数队列项。',
        )

    from types import SimpleNamespace
    monkeypatch.setattr(worker, '_heartbeat_loop', fake_heartbeat_loop)
    monkeypatch.setattr('app.services.background_task_worker_service.settings.sap_bom_base_url', 'https://sap.example.com')
    monkeypatch.setattr('app.sync.auto_bom_backfill_service.AutoBomBackfillService.consume', fake_consume)

    await worker.execute_task(task.id)

    await db_session.refresh(task)
    await db_session.refresh(job)
    assert task.status == BackgroundTaskStatus.SUCCEEDED.value
    assert job.status == 'completed'
    assert '当前没有待消费的 BOM 补数队列项' in (job.message or '')


@pytest.mark.asyncio
async def test_run_forever_claims_one_task_at_a_time(monkeypatch):
    worker = BackgroundTaskWorkerService()
    claimed_limits: list[int] = []

    async def fake_recover_stale_tasks() -> int:
        return 0

    async def fake_claim_once(*, limit: int):
        claimed_limits.append(limit)
        worker.stop()
        return []

    monkeypatch.setattr(worker, 'recover_stale_tasks', fake_recover_stale_tasks)
    monkeypatch.setattr(worker, 'claim_once', fake_claim_once)

    await worker.run_forever()

    assert claimed_limits == [1]


@pytest.mark.asyncio
async def test_heartbeat_refreshes_claimed_at_and_prevents_stale_recovery(db_session, monkeypatch):
    stale_time = utc_now() - timedelta(days=1)
    job = SyncJobLog(
        job_type='sales_plan',
        source_system='guandata',
        start_time=stale_time,
        heartbeat_at=stale_time,
        status='running',
        timeout_seconds=300,
        message='running',
    )
    db_session.add(job)
    await db_session.flush()

    task = BackgroundTask(
        task_type='sales_plan_sync',
        status=BackgroundTaskStatus.RUNNING.value,
        source='test',
        reason='queued',
        payload={'filter_payload': {'k': 'v'}},
        sync_job_log_id=job.id,
        attempt_count=1,
        max_attempts=2,
        available_at=stale_time,
        claimed_at=stale_time,
        started_at=stale_time,
        worker_id='worker-heartbeat',
    )
    db_session.add(task)
    await db_session.commit()

    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    worker = BackgroundTaskWorkerService(session_factory=session_factory)

    sleep_calls = 0

    async def fake_sleep(_seconds: float):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            return None
        raise asyncio.CancelledError()

    monkeypatch.setattr('app.services.background_task_worker_service.asyncio.sleep', fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await worker._heartbeat_loop(task.id)

    await db_session.refresh(task)
    await db_session.refresh(job)
    assert task.claimed_at is not None
    assert task.claimed_at > stale_time
    assert job.heartbeat_at is not None
    assert job.heartbeat_at > stale_time

    recovered = await worker.recover_stale_tasks()

    await db_session.refresh(task)
    assert recovered == 0
    assert task.status == BackgroundTaskStatus.RUNNING.value
    assert task.worker_id == 'worker-heartbeat'


@pytest.mark.asyncio
async def test_recover_stale_tasks_requeues_retryable_running_task(db_session):
    now = utc_now()
    stale_time = now - timedelta(days=1)
    job = SyncJobLog(
        job_type='sales_plan',
        source_system='guandata',
        start_time=stale_time,
        heartbeat_at=stale_time,
        status='running',
        timeout_seconds=300,
        message='running',
    )
    db_session.add(job)
    await db_session.flush()

    task = BackgroundTask(
        task_type='sales_plan_sync',
        status=BackgroundTaskStatus.RUNNING.value,
        source='test',
        reason='queued',
        payload={'filter_payload': {'k': 'v'}},
        sync_job_log_id=job.id,
        attempt_count=1,
        max_attempts=2,
        available_at=stale_time,
        claimed_at=stale_time,
        started_at=stale_time,
        worker_id='worker-stale',
    )
    db_session.add(task)
    await db_session.commit()

    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    worker = BackgroundTaskWorkerService(session_factory=session_factory)

    recovered = await worker.recover_stale_tasks()

    await db_session.refresh(task)
    await db_session.refresh(job)
    assert recovered == 1
    assert task.status == BackgroundTaskStatus.PENDING.value
    assert task.claimed_at is None
    assert task.started_at is None
    assert task.worker_id is None
    assert task.last_error is not None
    assert 'task_type=sales_plan_sync' in task.last_error
    assert 'worker-stale' in task.last_error
    assert 'action=requeue' in task.last_error
    assert task.available_at >= now
    assert job.status == 'queued'
    assert job.heartbeat_at is not None
    assert job.message is not None
    assert 'task_type=sales_plan_sync' in job.message


@pytest.mark.asyncio
async def test_recover_stale_tasks_marks_exhausted_running_task_failed(db_session):
    now = utc_now()
    stale_time = now - timedelta(days=1)
    job = SyncJobLog(
        job_type='sales_plan',
        source_system='guandata',
        start_time=stale_time,
        heartbeat_at=stale_time,
        status='running',
        timeout_seconds=300,
        message='running',
    )
    db_session.add(job)
    await db_session.flush()

    task = BackgroundTask(
        task_type='sales_plan_sync',
        status=BackgroundTaskStatus.RUNNING.value,
        source='test',
        reason='queued',
        payload={'filter_payload': {'k': 'v'}},
        sync_job_log_id=job.id,
        attempt_count=2,
        max_attempts=2,
        available_at=stale_time,
        claimed_at=stale_time,
        started_at=stale_time,
        worker_id='worker-stale',
    )
    db_session.add(task)
    await db_session.commit()

    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    worker = BackgroundTaskWorkerService(session_factory=session_factory)

    recovered = await worker.recover_stale_tasks()

    await db_session.refresh(task)
    await db_session.refresh(job)
    assert recovered == 1
    assert task.status == BackgroundTaskStatus.FAILED.value
    assert task.finished_at is not None
    assert task.last_error is not None
    assert 'task_type=sales_plan_sync' in task.last_error
    assert 'action=fail' in task.last_error
    assert job.status == 'completed_with_errors'
    assert job.fail_count == 1
    assert job.end_time is not None
    assert job.message is not None
    assert 'task_type=sales_plan_sync' in job.message
