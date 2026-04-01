from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.common.enums import SchedulerRuntimeState
from app.models.sync_scheduler_state import SyncSchedulerState
from app.sync_scheduler import (
    SyncSchedulerControlService,
    SyncSchedulerService,
    build_sync_scheduler_job_definitions,
)


class _DummySession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class _DummySessionFactory:
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


def test_sync_scheduler_registers_six_jobs():
    service = SyncSchedulerService(session_factory=_DummySessionFactory(_DummySession()))

    job_ids = {job.id for job in service.scheduler.get_jobs()}
    assert job_ids == {
        'sales_plan_sync',
        'bom_sync',
        'bom_backfill_queue_consume',
        'production_order_sync',
        'research_sync',
        'schedule_snapshot_reconcile',
    }


@pytest.mark.asyncio
async def test_dispatch_job_enqueues_sales_plan_background_task(monkeypatch):
    session = _DummySession()
    service = SyncSchedulerService(session_factory=_DummySessionFactory(session))
    definition = next(item for item in build_sync_scheduler_job_definitions() if item.id == 'sales_plan_sync')
    mock_enqueue = AsyncMock(return_value=(SimpleNamespace(id=11), SimpleNamespace(id=22), True))
    monkeypatch.setattr('app.sync_scheduler.BackgroundTaskDispatchService.enqueue', mock_enqueue)

    await service._build_dispatch_job(definition)()

    assert session.committed is True
    kwargs = mock_enqueue.await_args.kwargs
    assert kwargs['task_type'] == 'sales_plan_sync'
    assert kwargs['dedupe_key'] == 'sync_job:sales_plan:guandata'
    assert kwargs['sync_job_kwargs']['job_type'] == 'sales_plan'
    assert 'filter_payload' in kwargs['payload']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('definition_id', 'expected_job_type', 'expected_source_system'),
    [
        ('schedule_snapshot_reconcile', 'schedule_snapshot_reconcile', 'system'),
        ('bom_backfill_queue_consume', 'bom_backfill_queue', 'system'),
    ],
)
async def test_dispatch_job_enqueues_scheduler_logs_for_auto_tasks(
    monkeypatch,
    definition_id,
    expected_job_type,
    expected_source_system,
):
    session = _DummySession()
    service = SyncSchedulerService(session_factory=_DummySessionFactory(session))
    definition = next(item for item in build_sync_scheduler_job_definitions() if item.id == definition_id)
    mock_enqueue = AsyncMock(return_value=(SimpleNamespace(id=11), SimpleNamespace(id=22), True))
    monkeypatch.setattr('app.sync_scheduler.BackgroundTaskDispatchService.enqueue', mock_enqueue)

    await service._build_dispatch_job(definition)()

    assert session.committed is True
    kwargs = mock_enqueue.await_args.kwargs
    assert kwargs['task_type'] == definition.task_type
    assert kwargs['sync_job_kwargs']['job_type'] == expected_job_type
    assert kwargs['sync_job_kwargs']['source_system'] == expected_source_system
    assert kwargs['sync_job_kwargs']['message']


@pytest.mark.asyncio
async def test_dispatch_job_skips_commit_when_task_already_exists(monkeypatch):
    session = _DummySession()
    service = SyncSchedulerService(session_factory=_DummySessionFactory(session))
    definition = next(item for item in build_sync_scheduler_job_definitions() if item.id == 'bom_sync')
    mock_enqueue = AsyncMock(return_value=(SimpleNamespace(id=11), SimpleNamespace(id=22), False))
    monkeypatch.setattr('app.sync_scheduler.BackgroundTaskDispatchService.enqueue', mock_enqueue)

    await service._build_dispatch_job(definition)()

    assert session.rolled_back is True


@pytest.mark.asyncio
async def test_scheduler_control_status_returns_jobs(db_session):
    service = SyncSchedulerControlService(db_session)

    status = await service.get_status()

    assert status['state'] in {'stopped', 'paused'}
    assert len(status['jobs']) >= 5


@pytest.mark.asyncio
async def test_scheduler_control_heartbeat_updates_runtime_state(db_session):
    service = SyncSchedulerControlService(db_session)

    await service.heartbeat(instance_id='worker-1', state=SchedulerRuntimeState.RUNNING.value)

    entity = await db_session.get(SyncSchedulerState, 1)
    assert entity is not None
    assert entity.instance_id == 'worker-1'
    assert entity.last_state == SchedulerRuntimeState.RUNNING.value
    assert entity.heartbeat_at is not None


@pytest.mark.asyncio
async def test_scheduler_control_status_returns_running_when_heartbeat_is_fresh(db_session):
    service = SyncSchedulerControlService(db_session)
    await service.heartbeat(instance_id='worker-1', state=SchedulerRuntimeState.RUNNING.value)

    status = await service.get_status()

    assert status['state'] == SchedulerRuntimeState.RUNNING.value


@pytest.mark.asyncio
async def test_scheduler_control_status_returns_stopped_when_heartbeat_is_stale(db_session):
    service = SyncSchedulerControlService(db_session)
    await service.heartbeat(instance_id='worker-1', state=SchedulerRuntimeState.RUNNING.value)

    entity = await db_session.get(SyncSchedulerState, 1)
    assert entity is not None
    entity.heartbeat_at = datetime.now() - timedelta(days=1)
    await db_session.commit()

    status = await service.get_status()

    assert status['state'] == SchedulerRuntimeState.STOPPED.value


@pytest.mark.asyncio
async def test_scheduler_control_mark_stopped_ignores_other_instance(db_session):
    service = SyncSchedulerControlService(db_session)
    await service.heartbeat(instance_id='worker-1', state=SchedulerRuntimeState.RUNNING.value)

    before = await db_session.get(SyncSchedulerState, 1)
    assert before is not None
    original_heartbeat = before.heartbeat_at

    await service.mark_stopped(instance_id='worker-2')

    entity = await db_session.get(SyncSchedulerState, 1)
    assert entity is not None
    assert entity.instance_id == 'worker-1'
    assert entity.last_state == SchedulerRuntimeState.RUNNING.value
    assert entity.heartbeat_at == original_heartbeat


@pytest.mark.asyncio
async def test_scheduler_control_mark_stopped_updates_same_instance(db_session):
    service = SyncSchedulerControlService(db_session)
    await service.heartbeat(instance_id='worker-1', state=SchedulerRuntimeState.RUNNING.value)

    await service.mark_stopped(instance_id='worker-1')

    entity = await db_session.get(SyncSchedulerState, 1)
    assert entity is not None
    assert entity.instance_id == 'worker-1'
    assert entity.last_state == SchedulerRuntimeState.STOPPED.value
    assert entity.heartbeat_at is not None
