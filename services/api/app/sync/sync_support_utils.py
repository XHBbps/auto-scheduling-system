from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utc_now
from app.config import settings
from app.models.sync_job_log import SyncJobLog


@dataclass
class SyncResult:
    success_count: int = 0
    fail_count: int = 0
    insert_count: int = 0
    update_count: int = 0
    issue_count: int = 0

    def record_insert(self):
        self.success_count += 1
        self.insert_count += 1

    def record_update(self):
        self.success_count += 1
        self.update_count += 1

    def record_fail(self):
        self.fail_count += 1

    def record_issue(self):
        self.issue_count += 1


def _resolve_timeout_seconds(timeout_seconds: int | None = None) -> int:
    value = timeout_seconds if timeout_seconds is not None else settings.sync_job_timeout_seconds
    return max(int(value or 0), 1)


async def start_sync_job(
    session: AsyncSession,
    job_type: str,
    source_system: str,
    *,
    operator_name: str | None = None,
    timeout_seconds: int | None = None,
) -> SyncJobLog:
    now = utc_now()
    job = SyncJobLog(
        job_type=job_type,
        source_system=source_system,
        start_time=now,
        heartbeat_at=now,
        status="running",
        operator_name=operator_name,
        timeout_seconds=_resolve_timeout_seconds(timeout_seconds),
    )
    session.add(job)
    await session.flush()
    return job


async def touch_sync_job(
    session: AsyncSession,
    job: SyncJobLog,
    *,
    touched_at: datetime | None = None,
) -> SyncJobLog:
    job.heartbeat_at = touched_at or utc_now()
    await session.flush()
    return job


async def finish_sync_job(
    session: AsyncSession,
    job: SyncJobLog,
    result: SyncResult,
    message: str = "",
) -> SyncJobLog:
    now = utc_now()
    job.end_time = now
    job.heartbeat_at = now
    job.status = "completed" if result.fail_count == 0 else "completed_with_errors"
    job.success_count = result.success_count
    job.fail_count = result.fail_count
    job.message = message
    await session.flush()
    return job


def is_sync_job_stale(job: SyncJobLog, *, now: datetime | None = None) -> bool:
    if job.status != "running":
        return False
    current_time = now or utc_now()
    timeout_seconds = _resolve_timeout_seconds(job.timeout_seconds)
    last_active_at = job.heartbeat_at or job.start_time
    return last_active_at <= current_time - timedelta(seconds=timeout_seconds)


async def mark_sync_job_recovered(
    session: AsyncSession,
    job: SyncJobLog,
    *,
    note: str,
    recovered_at: datetime | None = None,
) -> SyncJobLog:
    now = recovered_at or utc_now()
    job.end_time = now
    job.heartbeat_at = now
    job.recovered_at = now
    job.recovery_note = note
    job.status = "failed"
    if not job.message:
        job.message = note
    else:
        job.message = f"{job.message}\n{note}"
    await session.flush()
    return job


async def recover_stale_sync_jobs(
    session: AsyncSession,
    job_type: str,
    source_system: str,
) -> list[SyncJobLog]:
    stmt = (
        select(SyncJobLog)
        .where(
            SyncJobLog.job_type == job_type,
            SyncJobLog.source_system == source_system,
            SyncJobLog.status == "running",
        )
        .order_by(SyncJobLog.id.asc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    recovered: list[SyncJobLog] = []
    for row in rows:
        if not is_sync_job_stale(row):
            continue
        timeout_seconds = _resolve_timeout_seconds(row.timeout_seconds)
        await mark_sync_job_recovered(
            session,
            row,
            note=(
                f"任务因心跳超时被自动回收："
                f"job_type={job_type}, source_system={source_system}, timeout_seconds={timeout_seconds}"
            ),
        )
        recovered.append(row)
    return recovered


async def get_running_sync_job(
    session: AsyncSession,
    job_type: str,
    source_system: str,
) -> SyncJobLog | None:
    await recover_stale_sync_jobs(session, job_type, source_system)
    stmt = (
        select(SyncJobLog)
        .where(
            SyncJobLog.job_type == job_type,
            SyncJobLog.source_system == source_system,
            SyncJobLog.status.in_(("queued", "running")),
        )
        .order_by(SyncJobLog.id.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()
