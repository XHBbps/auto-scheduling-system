from datetime import datetime, timedelta

import pytest

from app.common.datetime_utils import utc_now
from app.sync.sync_support_utils import (
    SyncResult,
    finish_sync_job,
    get_running_sync_job,
    start_sync_job,
    touch_sync_job,
)
from app.repository.sync_job_log_repo import SyncJobLogRepo


@pytest.mark.asyncio
async def test_sync_result_defaults():
    r = SyncResult()
    assert r.success_count == 0
    assert r.fail_count == 0
    assert r.insert_count == 0
    assert r.update_count == 0
    assert r.issue_count == 0


@pytest.mark.asyncio
async def test_sync_result_increment():
    r = SyncResult()
    r.record_insert()
    r.record_insert()
    r.record_update()
    r.record_fail()
    r.record_issue()
    assert r.success_count == 3
    assert r.insert_count == 2
    assert r.update_count == 1
    assert r.fail_count == 1
    assert r.issue_count == 1


@pytest.mark.asyncio
async def test_start_and_finish_sync_job(db_session):
    repo = SyncJobLogRepo(db_session)
    job = await start_sync_job(
        db_session,
        job_type="sales_plan",
        source_system="guandata",
        operator_name="测试管理员",
        timeout_seconds=60,
    )
    await db_session.commit()
    assert job.id is not None
    assert job.status == "running"
    assert job.operator_name == "测试管理员"
    assert job.timeout_seconds == 60
    assert job.heartbeat_at is not None

    result = SyncResult()
    result.record_insert()
    result.record_insert()
    result.record_fail()
    await finish_sync_job(db_session, job, result, message="done")
    await db_session.commit()
    assert job.status == "completed_with_errors"
    assert job.success_count == 2
    assert job.fail_count == 1
    assert job.end_time is not None


@pytest.mark.asyncio
async def test_get_running_sync_job_recovers_stale_job(db_session):
    job = await start_sync_job(
        db_session,
        job_type="sales_plan",
        source_system="guandata",
        timeout_seconds=1,
    )
    job.heartbeat_at = utc_now() - timedelta(seconds=10)
    await db_session.commit()

    running_job = await get_running_sync_job(db_session, "sales_plan", "guandata")
    await db_session.commit()

    assert running_job is None
    refreshed = await db_session.get(type(job), job.id)
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.recovered_at is not None
    assert "自动回收" in (refreshed.recovery_note or "")


@pytest.mark.asyncio
async def test_touch_sync_job_updates_heartbeat(db_session):
    job = await start_sync_job(db_session, job_type="bom", source_system="sap", timeout_seconds=30)
    old_heartbeat = job.heartbeat_at
    assert old_heartbeat is not None

    await touch_sync_job(
        db_session,
        job,
        touched_at=old_heartbeat + timedelta(seconds=5),
    )
    await db_session.commit()

    refreshed = await db_session.get(type(job), job.id)
    assert refreshed is not None
    assert refreshed.heartbeat_at == old_heartbeat + timedelta(seconds=5)
