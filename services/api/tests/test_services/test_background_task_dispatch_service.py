import logging

import pytest
from sqlalchemy import func, select

from app.models.background_task import BackgroundTask
from app.models.sync_job_log import SyncJobLog
from app.services.background_task_dispatch_service import BackgroundTaskDispatchService


@pytest.mark.asyncio
async def test_enqueue_creates_task_and_sync_job_log(db_session):
    service = BackgroundTaskDispatchService(db_session)

    task, job, created = await service.enqueue(
        task_type="sales_plan_sync",
        source="scheduler_job",
        reason="sales_plan_sync",
        payload={"filter_payload": {"days": 7}},
        dedupe_key="sync_job:sales_plan:guandata",
        sync_job_kwargs={
            "job_type": "sales_plan",
            "source_system": "guandata",
            "message": "scheduled sales plan sync",
        },
    )
    await db_session.commit()

    assert created is True
    assert task.id is not None
    assert task.sync_job_log_id == job.id
    assert task.dedupe_key == "sync_job:sales_plan:guandata"
    assert job is not None
    assert job.job_type == "sales_plan"
    assert job.source_system == "guandata"
    assert job.status == "queued"


@pytest.mark.asyncio
async def test_enqueue_logs_created_task(db_session, caplog):
    service = BackgroundTaskDispatchService(db_session)

    with caplog.at_level(logging.INFO):
        task, job, created = await service.enqueue(
            task_type="sales_plan_sync",
            source="scheduler_job",
            reason="sales_plan_sync",
            payload={"filter_payload": {"days": 7}},
            dedupe_key="sync_job:sales_plan:guandata",
            sync_job_kwargs={
                "job_type": "sales_plan",
                "source_system": "guandata",
                "message": "scheduled sales plan sync",
            },
        )

    assert created is True
    assert task.id is not None
    assert job is not None
    assert "Background task enqueued" in caplog.text
    assert "task_type=sales_plan_sync" in caplog.text
    assert "dedupe_key=sync_job:sales_plan:guandata" in caplog.text


@pytest.mark.asyncio
async def test_enqueue_reuses_existing_active_task_and_job_for_same_dedupe_key(db_session):
    service = BackgroundTaskDispatchService(db_session)

    first_task, first_job, first_created = await service.enqueue(
        task_type="sales_plan_sync",
        source="scheduler_job",
        reason="sales_plan_sync",
        payload={"filter_payload": {"days": 7}},
        dedupe_key="sync_job:sales_plan:guandata",
        sync_job_kwargs={
            "job_type": "sales_plan",
            "source_system": "guandata",
            "message": "scheduled sales plan sync",
        },
    )
    await db_session.commit()

    second_task, second_job, second_created = await service.enqueue(
        task_type="sales_plan_sync",
        source="scheduler_job",
        reason="sales_plan_sync_retry",
        payload={"filter_payload": {"days": 14}},
        dedupe_key="sync_job:sales_plan:guandata",
        sync_job_kwargs={
            "job_type": "sales_plan",
            "source_system": "guandata",
            "message": "should not create duplicate log",
        },
    )
    await db_session.commit()

    task_count = await db_session.scalar(select(func.count()).select_from(BackgroundTask))
    job_count = await db_session.scalar(select(func.count()).select_from(SyncJobLog))

    assert first_created is True
    assert second_created is False
    assert second_task.id == first_task.id
    assert second_job is not None
    assert first_job is not None
    assert second_job.id == first_job.id
    assert task_count == 1
    assert job_count == 1


@pytest.mark.asyncio
async def test_enqueue_logs_deduped_task(db_session, caplog):
    service = BackgroundTaskDispatchService(db_session)
    await service.enqueue(
        task_type="sales_plan_sync",
        source="scheduler_job",
        reason="sales_plan_sync",
        payload={"filter_payload": {"days": 7}},
        dedupe_key="sync_job:sales_plan:guandata",
        sync_job_kwargs={
            "job_type": "sales_plan",
            "source_system": "guandata",
            "message": "scheduled sales plan sync",
        },
    )
    await db_session.commit()

    with caplog.at_level(logging.INFO):
        task, job, created = await service.enqueue(
            task_type="sales_plan_sync",
            source="scheduler_job",
            reason="sales_plan_sync_retry",
            payload={"filter_payload": {"days": 14}},
            dedupe_key="sync_job:sales_plan:guandata",
            sync_job_kwargs={
                "job_type": "sales_plan",
                "source_system": "guandata",
                "message": "should not create duplicate log",
            },
        )

    assert created is False
    assert task.id is not None
    assert job is not None
    assert "Background task enqueue deduped" in caplog.text
    assert "existing_task_id=" in caplog.text


@pytest.mark.asyncio
async def test_enqueue_allows_recreate_after_existing_task_finished(db_session):
    service = BackgroundTaskDispatchService(db_session)

    first_task, first_job, first_created = await service.enqueue(
        task_type="schedule_snapshot_reconcile",
        source="scheduler_job",
        reason="schedule_snapshot_reconcile",
        payload=None,
        dedupe_key="scheduler:schedule_snapshot_reconcile",
        sync_job_kwargs=None,
    )
    await db_session.commit()

    first_task.status = "succeeded"
    await db_session.commit()

    second_task, second_job, second_created = await service.enqueue(
        task_type="schedule_snapshot_reconcile",
        source="scheduler_job",
        reason="schedule_snapshot_reconcile",
        payload=None,
        dedupe_key="scheduler:schedule_snapshot_reconcile",
        sync_job_kwargs=None,
    )
    await db_session.commit()

    task_count = await db_session.scalar(select(func.count()).select_from(BackgroundTask))

    assert first_created is True
    assert second_created is True
    assert first_job is None
    assert second_job is None
    assert second_task.id != first_task.id
    assert task_count == 2
