from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from socket import gethostname
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_PAUSED, STATE_RUNNING, STATE_STOPPED
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.datetime_utils import utc_now
from app.common.enums import SchedulerRuntimeState
from app.config import settings
from app.database import async_session_factory
from app.repository.sync_scheduler_state_repo import SyncSchedulerStateRepo
from app.services.background_task_dispatch_service import BackgroundTaskDispatchService
from app.sync.sales_plan_filters import build_sales_plan_filter_window, format_sales_plan_filter_window

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncSchedulerJobDefinition:
    id: str
    name: str
    trigger_factory: Callable[[ZoneInfo], object]
    task_type: str
    reason: str
    payload_factory: Callable[[], dict[str, Any] | None] | None = None
    sync_job_kwargs_factory: Callable[[], dict[str, Any] | None] | None = None
    source: str = "scheduler_job"

    def build_trigger(self, timezone: ZoneInfo):
        return self.trigger_factory(timezone)

    def build_payload(self) -> dict[str, Any] | None:
        return self.payload_factory() if self.payload_factory is not None else None

    def build_sync_job_kwargs(self) -> dict[str, Any] | None:
        return self.sync_job_kwargs_factory() if self.sync_job_kwargs_factory is not None else None


def build_sync_scheduler_job_definitions() -> list[SyncSchedulerJobDefinition]:
    def _sales_plan_payload() -> dict[str, Any]:
        window = build_sales_plan_filter_window(window_days=settings.sync_window_days)
        return {"filter_payload": window.filter_payload}

    def _sales_plan_job_kwargs() -> dict[str, Any]:
        window = build_sales_plan_filter_window(window_days=settings.sync_window_days)
        return {
            "job_type": "sales_plan",
            "source_system": "guandata",
            "message": f"调度触发销售计划同步，筛选条件：{format_sales_plan_filter_window(window)}。",
        }

    return [
        SyncSchedulerJobDefinition(
            id="sales_plan_sync",
            name="sales_plan_sync",
            trigger_factory=lambda timezone: CronTrigger(
                hour=settings.sales_plan_sync_hour,
                minute=settings.sales_plan_sync_minute,
                timezone=timezone,
            ),
            task_type="sales_plan_sync",
            reason="sales_plan_sync",
            payload_factory=_sales_plan_payload,
            sync_job_kwargs_factory=_sales_plan_job_kwargs,
        ),
        SyncSchedulerJobDefinition(
            id="bom_sync",
            name="bom_sync",
            trigger_factory=lambda timezone: CronTrigger(
                hour=settings.bom_sync_hour,
                minute=settings.bom_sync_minute,
                timezone=timezone,
            ),
            task_type="bom_sync",
            reason="bom_sync",
            payload_factory=lambda: {},
            sync_job_kwargs_factory=lambda: {
                "job_type": "bom",
                "source_system": "sap",
                "message": "调度触发 BOM 同步，任务已进入后台队列。",
            },
        ),
        SyncSchedulerJobDefinition(
            id="production_order_sync",
            name="production_order_sync",
            trigger_factory=lambda timezone: CronTrigger(
                hour=settings.production_order_sync_hour,
                minute=settings.production_order_sync_minute,
                timezone=timezone,
            ),
            task_type="production_order_sync",
            reason="production_order_sync",
            sync_job_kwargs_factory=lambda: {
                "job_type": "production_order",
                "source_system": "feishu",
                "message": "调度触发生产订单同步，任务已进入后台队列。",
            },
        ),
        SyncSchedulerJobDefinition(
            id="research_sync",
            name="research_sync",
            trigger_factory=lambda timezone: CronTrigger(
                hour=settings.research_sync_hour,
                minute=settings.research_sync_minute,
                timezone=timezone,
            ),
            task_type="research_sync",
            reason="research_sync",
            sync_job_kwargs_factory=lambda: {
                "job_type": "research",
                "source_system": "feishu",
                "message": "调度触发研究所数据同步，任务已进入后台队列。",
            },
        ),
        SyncSchedulerJobDefinition(
            id="schedule_snapshot_reconcile",
            name="schedule_snapshot_reconcile",
            trigger_factory=lambda timezone: CronTrigger(
                hour=settings.schedule_snapshot_reconcile_hour,
                minute=settings.schedule_snapshot_reconcile_minute,
                timezone=timezone,
            ),
            task_type="schedule_snapshot_reconcile",
            reason="schedule_snapshot_reconcile",
            sync_job_kwargs_factory=lambda: {
                "job_type": "schedule_snapshot_reconcile",
                "source_system": "system",
                "message": "调度触发排产快照对账任务。",
            },
        ),
        SyncSchedulerJobDefinition(
            id="bom_backfill_queue_consume",
            name="bom_backfill_queue_consume",
            trigger_factory=lambda timezone: IntervalTrigger(
                minutes=settings.bom_backfill_queue_consume_minutes,
                timezone=timezone,
            ),
            task_type="bom_backfill_queue_consume",
            reason="bom_backfill_queue_consume",
            sync_job_kwargs_factory=lambda: {
                "job_type": "bom_backfill_queue",
                "source_system": "system",
                "message": "调度触发 BOM 补录队列消费任务。",
            },
        ),
    ]


class SyncSchedulerControlService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SyncSchedulerStateRepo(session)

    async def get_status(self) -> dict[str, Any]:
        entity = await self.repo.get_singleton()
        state = self._resolve_runtime_state(entity.heartbeat_at, entity.last_state)
        return {
            "enabled": bool(entity.enabled),
            "state": state,
            "timezone": settings.sync_scheduler_timezone,
            "jobs": self._serialize_jobs(state=state),
        }

    async def set_enabled(self, enabled: bool | None, *, updated_by: str) -> dict[str, Any]:
        entity = await self.repo.get_singleton()
        if enabled is not None:
            entity.enabled = bool(enabled)
            entity.updated_by = updated_by
        await self.session.commit()
        return await self.get_status()

    async def heartbeat(self, *, instance_id: str, state: str) -> None:
        entity = await self.repo.get_singleton()
        entity.instance_id = instance_id
        entity.last_state = state
        entity.heartbeat_at = utc_now()
        await self.session.commit()

    async def mark_stopped(self, *, instance_id: str) -> None:
        entity = await self.repo.get_singleton()
        if entity.instance_id and entity.instance_id != instance_id:
            return
        entity.instance_id = instance_id
        entity.last_state = SchedulerRuntimeState.STOPPED.value
        entity.heartbeat_at = utc_now()
        await self.session.commit()

    async def is_enabled(self) -> bool:
        entity = await self.repo.get_singleton()
        return bool(entity.enabled)

    def _serialize_jobs(self, *, state: str) -> list[dict[str, Any]]:
        timezone = ZoneInfo(settings.sync_scheduler_timezone)
        now = datetime.now(timezone)
        items: list[dict[str, Any]] = []
        for definition in build_sync_scheduler_job_definitions():
            if definition.id == "bom_backfill_queue_consume" and (
                not settings.bom_backfill_queue_consume_enabled or settings.bom_backfill_queue_consume_minutes <= 0
            ):
                continue
            trigger = definition.build_trigger(timezone)
            next_run_time = trigger.get_next_fire_time(None, now)
            items.append(
                {
                    "id": definition.id,
                    "name": definition.name,
                    "next_run_time": next_run_time.isoformat() if next_run_time else None,
                }
            )
        return items

    @staticmethod
    def _resolve_runtime_state(heartbeat_at: datetime | None, last_state: str | None) -> str:
        if heartbeat_at is None:
            return SchedulerRuntimeState.STOPPED.value
        age_seconds = (utc_now() - heartbeat_at).total_seconds()
        if age_seconds > max(settings.sync_scheduler_stale_seconds, 1):
            return SchedulerRuntimeState.STOPPED.value
        return last_state or SchedulerRuntimeState.STOPPED.value


class SyncSchedulerService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
        *,
        instance_id: str | None = None,
    ):
        self.session_factory = session_factory
        self.instance_id = instance_id or f"{gethostname()}:{id(self)}"
        self.scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.sync_scheduler_timezone))
        self._definitions = build_sync_scheduler_job_definitions()
        self._last_runtime_state: str | None = None
        self._register_jobs()

    def _register_jobs(self) -> None:
        for definition in self._definitions:
            if definition.id == "bom_backfill_queue_consume" and (
                not settings.bom_backfill_queue_consume_enabled or settings.bom_backfill_queue_consume_minutes <= 0
            ):
                continue
            self.scheduler.add_job(
                self._build_dispatch_job(definition),
                trigger=definition.build_trigger(self.scheduler.timezone),
                id=definition.id,
                replace_existing=True,
                coalesce=True,
                max_instances=1,
            )

    def _build_dispatch_job(self, definition: SyncSchedulerJobDefinition):
        async def _job_wrapper():
            async with self.session_factory() as session:
                dispatcher = BackgroundTaskDispatchService(session)
                task, _, created = await dispatcher.enqueue(
                    task_type=definition.task_type,
                    source=definition.source,
                    reason=definition.reason,
                    payload=definition.build_payload(),
                    dedupe_key=self._build_dedupe_key(definition),
                    sync_job_kwargs=definition.build_sync_job_kwargs(),
                )
                if created:
                    await session.commit()
                    logger.info("Scheduled task enqueued: task_type=%s task_id=%s", definition.task_type, task.id)
                else:
                    await session.rollback()
                    logger.info(
                        "Scheduled task skipped because an active task already exists: task_type=%s dedupe_key=%s",
                        definition.task_type,
                        self._build_dedupe_key(definition),
                    )

        return _job_wrapper

    async def run_forever(self) -> None:
        if self.scheduler.state == STATE_STOPPED:
            self.scheduler.start(paused=True)
        logger.info(
            "Sync scheduler started: instance_id=%s timezone=%s", self.instance_id, settings.sync_scheduler_timezone
        )
        try:
            while True:
                await self._sync_control_state()
                await asyncio.sleep(max(settings.sync_scheduler_control_poll_seconds, 0.5))
        finally:
            if self.scheduler.state != STATE_STOPPED:
                self.scheduler.shutdown(wait=False)
            async with self.session_factory() as session:
                await SyncSchedulerControlService(session).mark_stopped(instance_id=self.instance_id)
            logger.info("Sync scheduler stopped: instance_id=%s", self.instance_id)

    async def _sync_control_state(self) -> None:
        async with self.session_factory() as session:
            control = SyncSchedulerControlService(session)
            enabled = await control.is_enabled()
            if enabled:
                if self.scheduler.state == STATE_STOPPED:
                    self.scheduler.start(paused=False)
                elif self.scheduler.state == STATE_PAUSED:
                    self.scheduler.resume()
                state = SchedulerRuntimeState.RUNNING.value
            else:
                if self.scheduler.state == STATE_STOPPED:
                    self.scheduler.start(paused=True)
                elif self.scheduler.state == STATE_RUNNING:
                    self.scheduler.pause()
                state = SchedulerRuntimeState.PAUSED.value
            if state != self._last_runtime_state:
                logger.info(
                    "Sync scheduler control state changed: instance_id=%s enabled=%s state=%s",
                    self.instance_id,
                    enabled,
                    state,
                )
                self._last_runtime_state = state
            await control.heartbeat(instance_id=self.instance_id, state=state)

    @staticmethod
    def _build_dedupe_key(definition: SyncSchedulerJobDefinition) -> str:
        if definition.task_type == "sales_plan_sync":
            return "sync_job:sales_plan:guandata"
        if definition.task_type == "bom_sync":
            return "sync_job:bom:sap"
        if definition.task_type == "production_order_sync":
            return "sync_job:production_order:feishu"
        if definition.task_type == "research_sync":
            return "sync_job:research:feishu"
        return f"scheduler:{definition.task_type}"
