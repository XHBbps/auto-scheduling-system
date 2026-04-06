from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utc_now
from app.config import settings
from app.models.background_task import BackgroundTask
from app.models.sync_job_log import SyncJobLog
from app.repository.background_task_repo import BackgroundTaskRepo
from app.sync.sync_support_utils import _resolve_timeout_seconds

logger = logging.getLogger(__name__)


class BackgroundTaskDispatchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BackgroundTaskRepo(session)

    async def enqueue(
        self,
        *,
        task_type: str,
        source: str,
        reason: str | None = None,
        payload: dict[str, Any] | None = None,
        dedupe_key: str | None = None,
        sync_job_kwargs: dict[str, Any] | None = None,
        max_attempts: int | None = None,
    ) -> tuple[BackgroundTask, SyncJobLog | None, bool]:
        existing = await self.repo.get_active_by_dedupe_key(dedupe_key)
        if existing is not None:
            existing_job = None
            if existing.sync_job_log_id:
                existing_job = await self.session.get(SyncJobLog, existing.sync_job_log_id)
            logger.info(
                "Background task enqueue deduped: task_type=%s existing_task_id=%s dedupe_key=%s sync_job_log_id=%s",
                task_type,
                existing.id,
                dedupe_key,
                existing.sync_job_log_id,
            )
            return existing, existing_job, False

        job = None
        if sync_job_kwargs is not None:
            now = utc_now()
            job = SyncJobLog(
                job_type=sync_job_kwargs["job_type"],
                source_system=sync_job_kwargs["source_system"],
                start_time=now,
                heartbeat_at=now,
                status="queued",
                operator_name=sync_job_kwargs.get("operator_name"),
                timeout_seconds=_resolve_timeout_seconds(sync_job_kwargs.get("timeout_seconds")),
                message=sync_job_kwargs.get("message"),
            )
            self.session.add(job)
            await self.session.flush()

        task = BackgroundTask(
            task_type=task_type,
            status="pending",
            source=source,
            reason=reason,
            payload=payload,
            dedupe_key=dedupe_key,
            sync_job_log_id=job.id if job is not None else None,
            max_attempts=max_attempts if max_attempts is not None else settings.sync_task_default_max_attempts,
            available_at=utc_now(),
        )
        self.session.add(task)
        await self.session.flush()
        logger.info(
            "Background task enqueued: task_type=%s task_id=%s source=%s reason=%s dedupe_key=%s sync_job_log_id=%s",
            task_type,
            task.id,
            source,
            reason,
            dedupe_key,
            job.id if job is not None else None,
        )
        return task, job, True
