from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from socket import gethostname
from time import perf_counter
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.baseline.part_cycle_baseline_service import PartCycleBaselineService
from app.common.datetime_utils import utc_now
from app.common.enums import BackgroundTaskStatus
from app.common.exceptions import BizException, ErrorCode
from app.common.metrics import background_task_duration_seconds, background_task_total
from app.config import settings
from app.database import async_session_factory
from app.integration.feishu_client import FeishuClient
from app.integration.guandata_client import GuandataClient
from app.integration.sap_bom_client import SapBomClient
from app.models.background_task import BackgroundTask
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.sync_job_log import SyncJobLog
from app.repository.background_task_repo import BackgroundTaskRepo
from app.services.background_task_dispatch_service import BackgroundTaskDispatchService
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService
from app.sync.auto_bom_backfill_service import AutoBomBackfillService
from app.sync.bom_sync_service import BomSyncService
from app.sync.production_order_sync_service import ProductionOrderSyncService
from app.sync.sync_job_message_templates import (
    bom_missing_sap_message,
    bom_result_message,
    part_cycle_baseline_rebuild_result_message,
    production_order_result_message,
    queue_consume_empty_message,
    research_result_message,
    sales_plan_result_message,
)
from app.sync.sync_support_utils import SyncResult, finish_sync_job, touch_sync_job
from app.sync.sync_workflow_service import SyncWorkflowService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BackgroundTaskExecutionContext:
    task_id: int
    task_type: str
    payload: dict[str, Any]
    sync_job_log_id: int | None


def _classify_task_exception(exc: Exception) -> str:
    if isinstance(exc, BizException):
        return {
            ErrorCode.PARAM_ERROR: "param_error",
            ErrorCode.NOT_FOUND: "not_found",
            ErrorCode.BIZ_VALIDATION_FAILED: "biz_validation_failed",
            ErrorCode.EXTERNAL_API_FAILED: "external_api_failed",
            ErrorCode.DB_ERROR: "db_error",
            ErrorCode.SCHEDULE_CALC_FAILED: "schedule_calc_failed",
            ErrorCode.EXPORT_FAILED: "export_failed",
        }.get(exc.code, "biz_exception")
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, httpx.TimeoutException)):
        return "timeout"
    if isinstance(exc, httpx.RequestError):
        return "external_request_error"
    if isinstance(exc, ValueError) and "Unsupported background task type" in str(exc):
        return "unsupported_task_type"
    return "unexpected_error"


def _build_task_failure_message(
    *,
    task_id: int,
    task_type: str,
    stage: str,
    failure_kind: str,
    exc: Exception,
) -> str:
    return f"task_id={task_id}; task_type={task_type}; stage={stage}; failure_kind={failure_kind}; error={exc}"


class BackgroundTaskWorkerService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
        *,
        worker_id: str | None = None,
    ):
        self.session_factory = session_factory
        self.worker_id = worker_id or f"{gethostname()}:{id(self)}"
        self._stopping = False

    async def run_forever(self) -> None:
        logger.info("Background task worker started: worker_id=%s", self.worker_id)
        while not self._stopping:
            recovered = await self.recover_stale_tasks()
            if recovered:
                logger.warning("Recovered %s stale background tasks.", recovered)
            claimed = await self.claim_once(limit=1)
            if not claimed:
                await asyncio.sleep(max(settings.sync_task_worker_poll_interval_seconds, 0.1))
                continue
            await self.execute_task(claimed[0].id)

    def stop(self) -> None:
        self._stopping = True

    async def recover_stale_tasks(self) -> int:
        stale_before = utc_now() - timedelta(seconds=max(settings.sync_task_claim_timeout_seconds, 1))
        async with self.session_factory() as session:
            repo = BackgroundTaskRepo(session)
            stale_tasks = await repo.list_stale_running(stale_before=stale_before)
            recovered = 0
            for task in stale_tasks:
                job = await self._load_job(session, task)
                stale_worker_id = task.worker_id or "unknown"
                action = "requeue" if int(task.attempt_count or 0) < int(task.max_attempts or 1) else "fail"
                note = (
                    "后台任务认领超时已回收："
                    f"task_id={task.id}; task_type={task.task_type}; "
                    f"worker_id={stale_worker_id}; "
                    f"attempt={int(task.attempt_count or 0)}/{int(task.max_attempts or 1)}; "
                    f"action={action}"
                )
                if int(task.attempt_count or 0) < int(task.max_attempts or 1):
                    task.status = BackgroundTaskStatus.PENDING.value
                    # Add cooldown before re-availability to prevent concurrent
                    # execution if the original task is still finishing up.
                    cooldown = max(settings.sync_task_retry_backoff_seconds, 10)
                    task.available_at = utc_now() + timedelta(seconds=cooldown)
                    task.claimed_at = None
                    task.started_at = None
                    task.worker_id = None
                    task.last_error = note
                    if job is not None:
                        job.status = "queued"
                        job.heartbeat_at = utc_now()
                        job.message = note if not job.message else f"{job.message}\n{note}"
                else:
                    task.status = BackgroundTaskStatus.FAILED.value
                    task.finished_at = utc_now()
                    task.last_error = note
                    if job is not None:
                        result = SyncResult()
                        result.record_fail()
                        await finish_sync_job(session, job, result, note)
                logger.warning(
                    "Recovered stale background task: task_id=%s task_type=%s action=%s worker_id=%s attempts=%s/%s",
                    task.id,
                    task.task_type,
                    action,
                    stale_worker_id,
                    int(task.attempt_count or 0),
                    int(task.max_attempts or 1),
                )
                recovered += 1
            if recovered:
                await session.commit()
            return recovered

    async def claim_once(self, *, limit: int) -> list[BackgroundTask]:
        async with self.session_factory() as session:
            repo = BackgroundTaskRepo(session)
            tasks = await repo.claim_available(worker_id=self.worker_id, limit=limit)
            if tasks:
                await session.commit()
            return tasks

    async def _verify_task_ownership(self, task_id: int) -> bool:
        """Check that this task is still RUNNING and assigned to the current worker.

        Guards against the race where a task is recovered and reassigned
        between claim and execution start.
        """
        async with self.session_factory() as session:
            task = await session.get(BackgroundTask, task_id)
            if task is None or task.status != BackgroundTaskStatus.RUNNING.value:
                return False
            # If worker_id doesn't match, another worker took over.
            return task.worker_id is None or task.worker_id == self.worker_id

    async def execute_task(self, task_id: int) -> None:
        heartbeat_task: asyncio.Task | None = None
        heartbeat_lost = asyncio.Event()
        task_context: BackgroundTaskExecutionContext | None = None
        started_perf = perf_counter()
        try:
            task_context = await self._load_task_execution_context(task_id)
            if task_context is None:
                logger.warning("Background task execution skipped: task_id=%s reason=task_not_running", task_id)
                return
            await self._mark_task_started(task_id)
            # Verify ownership before starting execution to guard against
            # the task being recovered and reassigned between claim and start.
            if not await self._verify_task_ownership(task_id):
                logger.warning(
                    "Background task execution aborted: task_id=%s reason=ownership_lost",
                    task_id,
                )
                return
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(task_id, heartbeat_lost))
            logger.info(
                "Background task execution started: task_id=%s task_type=%s sync_job_log_id=%s worker_id=%s",
                task_context.task_id,
                task_context.task_type,
                task_context.sync_job_log_id,
                self.worker_id,
            )
            await self._execute_by_type(task_context)
            await self._mark_task_succeeded(task_id)
            background_task_total.labels(task_type=task_context.task_type, status="succeeded").inc()
            background_task_duration_seconds.labels(task_type=task_context.task_type).observe(
                perf_counter() - started_perf
            )
            logger.info(
                "Background task execution succeeded: task_id=%s task_type=%s sync_job_log_id=%s duration_ms=%s",
                task_context.task_id,
                task_context.task_type,
                task_context.sync_job_log_id,
                round((perf_counter() - started_perf) * 1000, 2),
            )
        except Exception as exc:
            task_type = task_context.task_type if task_context is not None else "unknown"
            sync_job_log_id = task_context.sync_job_log_id if task_context is not None else None
            failure_kind = _classify_task_exception(exc)
            message = _build_task_failure_message(
                task_id=task_id,
                task_type=task_type,
                stage="execute_task",
                failure_kind=failure_kind,
                exc=exc,
            )
            background_task_total.labels(task_type=task_type, status="failed").inc()
            background_task_duration_seconds.labels(task_type=task_type).observe(perf_counter() - started_perf)
            logger.exception(
                "Background task execution failed: task_id=%s task_type=%s sync_job_log_id=%s failure_kind=%s duration_ms=%s",
                task_id,
                task_type,
                sync_job_log_id,
                failure_kind,
                round((perf_counter() - started_perf) * 1000, 2),
            )
            await self._mark_task_failed(task_id, message)
        finally:
            if heartbeat_task is not None:
                heartbeat_task.cancel()
                await asyncio.gather(heartbeat_task, return_exceptions=True)

    async def _mark_task_failed(self, task_id: int, message: str) -> None:
        async with self.session_factory() as session:
            task = await session.get(BackgroundTask, task_id)
            if task is None:
                return
            job = await self._load_job(session, task)
            attempts = int(task.attempt_count or 0)
            max_attempts = max(int(task.max_attempts or 1), 1)
            retryable = attempts < max_attempts
            now = utc_now()
            task.last_error = message
            if retryable:
                task.status = BackgroundTaskStatus.PENDING.value
                task.available_at = now + timedelta(seconds=max(settings.sync_task_retry_backoff_seconds, 1))
                task.claimed_at = None
                task.started_at = None
                task.worker_id = None
                if job is not None:
                    job.status = "queued"
                    job.heartbeat_at = now
                    job.message = message
            else:
                task.status = BackgroundTaskStatus.FAILED.value
                task.finished_at = now
                if job is not None:
                    result = SyncResult()
                    result.record_fail()
                    await finish_sync_job(session, job, result, message)
            await session.commit()

    async def _heartbeat_loop(self, task_id: int, lost_event: asyncio.Event | None = None) -> None:
        interval_seconds = max(int(settings.sync_job_heartbeat_interval_seconds), 1)
        try:
            while True:
                await asyncio.sleep(interval_seconds)
                async with self.session_factory() as session:
                    task = await session.get(BackgroundTask, task_id)
                    if task is None or task.status != BackgroundTaskStatus.RUNNING.value:
                        if lost_event is not None:
                            lost_event.set()
                        return
                    # If task was reassigned to another worker, stop heartbeat.
                    if task.worker_id != self.worker_id:
                        logger.warning(
                            "Heartbeat stopping: task_id=%s reassigned to worker_id=%s",
                            task_id,
                            task.worker_id,
                        )
                        if lost_event is not None:
                            lost_event.set()
                        return
                    now = utc_now()
                    task.claimed_at = now
                    job = await self._load_job(session, task)
                    if job is not None and job.status == "running":
                        await touch_sync_job(session, job, touched_at=now)
                    await session.commit()
        except asyncio.CancelledError:
            raise

    async def _load_task_execution_context(self, task_id: int) -> BackgroundTaskExecutionContext | None:
        async with self.session_factory() as session:
            task = await session.get(BackgroundTask, task_id)
            if task is None or task.status != BackgroundTaskStatus.RUNNING.value:
                return None
            return BackgroundTaskExecutionContext(
                task_id=task.id,
                task_type=task.task_type,
                payload=dict(task.payload or {}),
                sync_job_log_id=task.sync_job_log_id,
            )

    async def _mark_task_started(self, task_id: int) -> None:
        async with self.session_factory() as session:
            task = await session.get(BackgroundTask, task_id)
            if task is None or task.status != BackgroundTaskStatus.RUNNING.value:
                return
            now = utc_now()
            task.started_at = now
            task.worker_id = self.worker_id
            job = await self._load_job(session, task)
            if job is not None:
                job.status = "running"
                if job.start_time is None:
                    job.start_time = now
                job.heartbeat_at = now
            await session.commit()

    async def _mark_task_succeeded(self, task_id: int) -> None:
        async with self.session_factory() as session:
            task = await session.get(BackgroundTask, task_id)
            if task is None:
                return
            task.status = BackgroundTaskStatus.SUCCEEDED.value
            task.finished_at = utc_now()
            task.last_error = None
            await session.commit()

    async def _execute_by_type(self, task: BackgroundTaskExecutionContext) -> None:
        async with self.session_factory() as session:
            if task.task_type == "sales_plan_sync":
                await self._execute_sales_plan(session, task, task.payload)
                return
            if task.task_type == "bom_sync":
                await self._execute_bom(session, task, task.payload)
                return
            if task.task_type == "production_order_sync":
                await self._execute_production_orders(session, task)
                return
            if task.task_type == "part_cycle_baseline_rebuild":
                await self._execute_part_cycle_baseline_rebuild(session, task)
                return
            if task.task_type == "research_sync":
                await self._execute_research(session, task, task.payload)
                return
            if task.task_type == "schedule_snapshot_reconcile":
                await self._execute_snapshot_reconcile(session, task)
                return
            if task.task_type == "bom_backfill_queue_consume":
                await self._execute_bom_backfill_queue_consume(task)
                return
            raise ValueError(f"Unsupported background task type: {task.task_type}")

    async def _execute_sales_plan(
        self,
        session: AsyncSession,
        task: BackgroundTaskExecutionContext,
        payload: dict[str, Any],
    ) -> None:
        job = await self._load_job(session, task)
        workflow_result = await SyncWorkflowService(session).sync_sales_plan(
            client=self._build_guandata_client(),
            filters=payload.get("filter_payload"),
            job=job,
        )
        if job is not None:
            job.message = sales_plan_result_message(
                success_count=workflow_result.sync_result.success_count,
                fail_count=workflow_result.sync_result.fail_count,
                drawing_updated_count=workflow_result.drawing_updated_count,
                enqueued_items=workflow_result.auto_bom_backfill.enqueued_items
                if workflow_result.auto_bom_backfill
                else 0,
                reactivated_items=workflow_result.auto_bom_backfill.reactivated_items
                if workflow_result.auto_bom_backfill
                else 0,
            )
        await session.commit()

    async def _execute_bom(
        self,
        session: AsyncSession,
        task: BackgroundTaskExecutionContext,
        payload: dict[str, Any],
    ) -> None:
        items = [(str(material_no), str(plant)) for material_no, plant in payload.get("items", [])]
        if not items:
            items = await self._get_bom_sync_items(session)
        job = await self._load_job(session, task)
        result = await BomSyncService(session, self._build_sap_bom_client()).sync_batch(items, job=job)
        if job is not None:
            job.message = bom_result_message(
                success_count=result.success_count,
                fail_count=result.fail_count,
                item_count=len(items),
            )
        await session.commit()

    async def _execute_production_orders(
        self,
        session: AsyncSession,
        task: BackgroundTaskExecutionContext,
    ) -> None:
        job = await self._load_job(session, task)
        sync_service = ProductionOrderSyncService(
            session,
            self._build_feishu_client(),
            app_token=settings.feishu_production_app_token,
            table_id=settings.feishu_production_table_id,
        )
        result = await sync_service.sync(job=job)
        rebuild_created = False
        if not sync_service.has_fetch_error and (
            int(result.insert_count or 0) > 0 or int(result.update_count or 0) > 0
        ):
            _, _, rebuild_created = await BackgroundTaskDispatchService(session).enqueue(
                task_type="part_cycle_baseline_rebuild",
                source="production_order_sync",
                reason="production_order_sync_completed",
                dedupe_key="baseline_rebuild:part_cycle",
                payload={
                    "trigger": "production_order_sync",
                    "source_insert_count": int(result.insert_count or 0),
                    "source_update_count": int(result.update_count or 0),
                },
            )
        if job is not None:
            job.message = production_order_result_message(
                success_count=result.success_count,
                fail_count=result.fail_count,
                baseline_rebuild_enqueued=1 if rebuild_created else 0,
            )
        await session.commit()

    async def _execute_part_cycle_baseline_rebuild(
        self,
        session: AsyncSession,
        task: BackgroundTaskExecutionContext,
    ) -> None:
        job = await self._load_job(session, task)
        rebuild_result = await PartCycleBaselineService(session).rebuild(
            persist_changes=True,
            refresh_source="part_cycle_baseline_rebuild",
            refresh_reason=task.payload.get("trigger") or task.task_type,
        )
        if job is not None:
            snapshot_refresh = rebuild_result.get("snapshot_refresh") or {}
            message = part_cycle_baseline_rebuild_result_message(
                eligible_groups=int(rebuild_result.get("eligible_groups", 0) or 0),
                promoted_groups=int(rebuild_result.get("promoted_groups", 0) or 0),
                persisted_groups=int(rebuild_result.get("persisted_groups", 0) or 0),
                manual_protected_groups=int(rebuild_result.get("manual_protected_groups", 0) or 0),
                deactivated_groups=int(rebuild_result.get("deactivated_groups", 0) or 0),
                snapshot_refreshed=int(snapshot_refresh.get("refreshed", 0) or 0),
            )
            result = SyncResult()
            result.record_update()
            await finish_sync_job(session, job, result, message)
        await session.commit()

    async def _execute_research(
        self,
        session: AsyncSession,
        task: BackgroundTaskExecutionContext,
        payload: dict[str, Any],
    ) -> None:
        job = await self._load_job(session, task)
        workflow_result = await SyncWorkflowService(session).sync_research(
            client=self._build_feishu_client(),
            app_token=settings.feishu_research_app_token,
            table_id=settings.feishu_research_table_id,
            order_no_filter=payload.get("order_no_filter"),
            job=job,
        )
        if job is not None:
            rebuild = workflow_result.machine_cycle_baseline_rebuild or {}
            auto_bom = workflow_result.auto_bom_backfill
            job.message = research_result_message(
                success_count=workflow_result.sync_result.success_count,
                fail_count=workflow_result.sync_result.fail_count,
                drawing_updated_count=workflow_result.drawing_updated_count,
                baseline_groups_processed=rebuild.get("groups_processed", 0),
                enqueued_items=auto_bom.enqueued_items if auto_bom else 0,
                reactivated_items=auto_bom.reactivated_items if auto_bom else 0,
            )
        await session.commit()

    async def _execute_snapshot_reconcile(self, session: AsyncSession, task: BackgroundTaskExecutionContext) -> None:
        job = await self._load_job(session, task)
        result_payload = await ScheduleSnapshotRefreshService(session).rebuild_all_open_snapshots(
            source="scheduler_job",
            reason="schedule_snapshot_reconcile",
        )
        if job is not None:
            message = (
                "快照对账完成："
                f"总处理 {int(result_payload.get('total', 0) or 0)} 条；"
                f"刷新 {int(result_payload.get('refreshed', 0) or 0)} 条；"
                f"scheduled {int(result_payload.get('scheduled', 0) or 0)} 条；"
                f"scheduled_stale {int(result_payload.get('scheduled_stale', 0) or 0)} 条；"
                f"删除 {int(result_payload.get('deleted', 0) or 0)} 条。"
            )
            result = SyncResult(success_count=int(result_payload.get("refreshed", 0) or 0))
            await finish_sync_job(session, job, result, message)
        await session.commit()

    async def _execute_bom_backfill_queue_consume(self, task: BackgroundTaskExecutionContext) -> None:
        if not settings.sap_bom_base_url:
            logger.warning("Skip bom_backfill_queue_consume task because sap_bom_base_url is missing.")
            if task.sync_job_log_id is not None:
                async with self.session_factory() as session:
                    job = await session.get(SyncJobLog, task.sync_job_log_id)
                    if job is not None and job.status not in {"completed", "completed_with_errors", "failed"}:
                        message = bom_missing_sap_message(source="scheduler_job", reason="bom_backfill_queue_consume")
                        result = SyncResult()
                        result.record_fail()
                        await finish_sync_job(session, job, result, message)
                        await session.commit()
            return
        result_payload = await AutoBomBackfillService(self.session_factory).consume(
            source="scheduler_job",
            reason="bom_backfill_queue_consume",
            sap_bom_base_url=settings.sap_bom_base_url,
            existing_job_id=task.sync_job_log_id,
        )
        if task.sync_job_log_id is None:
            return
        async with self.session_factory() as session:
            job = await session.get(SyncJobLog, task.sync_job_log_id)
            if job is None:
                return
            if job.status in {"completed", "completed_with_errors", "failed"}:
                return
            message = result_payload.message or queue_consume_empty_message(
                source="scheduler_job",
                reason="bom_backfill_queue_consume",
            )
            sync_result = SyncResult(
                success_count=int(result_payload.total_success_rows or 0),
                fail_count=int(result_payload.total_fail_rows or 0),
                insert_count=int(result_payload.total_success_rows or 0),
            )
            await finish_sync_job(session, job, sync_result, message)
            await session.commit()

    async def _load_job(
        self,
        session: AsyncSession,
        task: BackgroundTask | BackgroundTaskExecutionContext,
    ) -> SyncJobLog | None:
        if not task.sync_job_log_id:
            return None
        return await session.get(SyncJobLog, task.sync_job_log_id)

    @staticmethod
    async def _get_bom_sync_items(session: AsyncSession) -> list[tuple[str, str]]:
        stmt = (
            select(
                SalesPlanOrderLineSrc.material_no,
                SalesPlanOrderLineSrc.delivery_plant,
            )
            .where(SalesPlanOrderLineSrc.material_no.is_not(None))
            .distinct()
        )
        rows = (await session.execute(stmt)).all()
        items: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for material_no, plant in rows:
            item = (material_no, plant or "1000")
            if item not in seen:
                seen.add(item)
                items.append(item)
        return items

    @staticmethod
    def _build_guandata_client() -> GuandataClient:
        return GuandataClient(
            base_url=settings.guandata_base_url,
            domain=settings.guandata_domain,
            login_id=settings.guandata_login_id,
            password=settings.guandata_password,
            ds_id=settings.guandata_ds_id,
        )

    @staticmethod
    def _build_feishu_client() -> FeishuClient:
        return FeishuClient(
            app_id=settings.feishu_app_id,
            app_secret=settings.feishu_app_secret,
        )

    @staticmethod
    def _build_sap_bom_client() -> SapBomClient:
        return SapBomClient(base_url=settings.sap_bom_base_url)
