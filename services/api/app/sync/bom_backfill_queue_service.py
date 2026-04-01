import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import exists, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.datetime_utils import utc_now
from app.common.enums import BomBackfillFailureKind, BomBackfillQueueStatus
from app.config import settings
from app.database import async_session_factory as default_async_session_factory
from app.integration.sap_bom_client import SapBomClient
from app.models.bom_backfill_queue import BomBackfillQueue
from app.models.bom_relation import BomRelationSrc
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.sync_job_log import SyncJobLog
from app.repository.bom_backfill_queue_repo import BomBackfillQueueRepo
from app.sync.bom_sync_service import BomSyncExecutionResult, BomSyncService
from app.sync.sync_support_utils import SyncResult, finish_sync_job, get_running_sync_job, start_sync_job
from app.sync.sync_job_message_templates import (
    auto_bom_enqueue_empty_message,
    auto_bom_enqueue_summary_message,
    queue_consume_completed_message,
    queue_consume_empty_message,
    queue_consume_failed_message,
    queue_consume_progress_message,
    queue_consume_running_message,
    queue_consume_started_message,
)

logger = logging.getLogger(__name__)


@dataclass
class AutoBomBackfillResult:
    job_id: int | None = None
    created: bool = False
    skipped_running: bool = False
    candidate_orders: int = 0
    candidate_items: int = 0
    enqueued_items: int = 0
    reactivated_items: int = 0
    already_tracked_items: int = 0
    synced_items: int = 0
    deferred_items: int = 0
    success_count: int = 0
    fail_count: int = 0
    refreshed_order_count: int = 0
    closed_issue_count: int = 0
    processed_batches: int = 0
    message: str = ""


@dataclass
class BomBackfillQueueConsumeResult:
    job_id: int | None = None
    claimed_items: int = 0
    processed_items: int = 0
    success_items: int = 0
    retry_wait_items: int = 0
    failed_items: int = 0
    total_success_rows: int = 0
    total_fail_rows: int = 0
    message: str = ""


def serialize_bom_backfill_queue_item(entity: BomBackfillQueue) -> dict[str, Any]:
    return {
        "id": entity.id,
        "material_no": entity.material_no,
        "plant": entity.plant,
        "source": entity.source,
        "trigger_reason": entity.trigger_reason,
        "status": entity.status,
        "priority": entity.priority,
        "fail_count": entity.fail_count,
        "failure_kind": entity.failure_kind,
        "last_error": entity.last_error,
        "next_retry_at": entity.next_retry_at.isoformat() if entity.next_retry_at else None,
        "first_detected_at": entity.first_detected_at.isoformat() if entity.first_detected_at else None,
        "last_attempt_at": entity.last_attempt_at.isoformat() if entity.last_attempt_at else None,
        "resolved_at": entity.resolved_at.isoformat() if entity.resolved_at else None,
        "last_job_id": entity.last_job_id,
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
    }


class BomBackfillQueueService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        self.session_factory = session_factory or default_async_session_factory

    async def enqueue_candidates(
        self,
        *,
        source: str,
        reason: str,
        order_line_ids: list[int] | None = None,
    ) -> AutoBomBackfillResult:
        async with self.session_factory() as session:
            queue_repo = BomBackfillQueueRepo(session)
            candidates = await self._load_candidates(session, order_line_ids)
            result = AutoBomBackfillResult(
                candidate_orders=len(candidates["order_ids"]),
                candidate_items=len(candidates["items"]),
            )
            if not candidates["items"]:
                result.message = auto_bom_enqueue_empty_message(source=source, reason=reason)
                return result

            existing_items = await queue_repo.find_by_material_plants(candidates["items"])

            for material_no, plant in candidates["items"]:
                entity = existing_items.get((material_no, plant))
                action = await self._upsert_queue_item(
                    session=session,
                    entity=entity,
                    material_no=material_no,
                    plant=plant,
                    source=source,
                    reason=reason,
                )
                if action == "enqueued":
                    result.enqueued_items += 1
                elif action == "reactivated":
                    result.reactivated_items += 1
                else:
                    result.already_tracked_items += 1

            await session.commit()
            result.created = result.enqueued_items > 0 or result.reactivated_items > 0
            result.message = auto_bom_enqueue_summary_message(
                candidate_orders=result.candidate_orders,
                candidate_items=result.candidate_items,
                enqueued_items=result.enqueued_items,
                reactivated_items=result.reactivated_items,
                already_tracked_items=result.already_tracked_items,
            )
            return result

    async def consume_queue(
        self,
        *,
        source: str,
        reason: str,
        sap_bom_base_url: str,
        existing_job_id: int | None = None,
    ) -> BomBackfillQueueConsumeResult:
        result = BomBackfillQueueConsumeResult()
        max_items = max(1, settings.auto_bom_backfill_max_items_per_run)

        async with self.session_factory() as session:
            if existing_job_id is None:
                running_job = await get_running_sync_job(session, "bom", "sap")
                if running_job:
                    result.job_id = running_job.id
                    result.message = queue_consume_running_message(
                        source=source,
                        reason=reason,
                        running_job_id=running_job.id,
                    )
                    return result

            queue_repo = BomBackfillQueueRepo(session)
            claimed = await queue_repo.claim_batch(max_items)
            job = await session.get(SyncJobLog, existing_job_id) if existing_job_id is not None else None
            if not claimed:
                result.job_id = existing_job_id
                result.message = queue_consume_empty_message(source=source, reason=reason)
                if job is not None:
                    await finish_sync_job(session, job, SyncResult(), result.message)
                await session.commit()
                return result

            if job is None:
                job = await start_sync_job(session, "bom", "sap")
            job.message = queue_consume_started_message(
                claimed_items=len(claimed),
                batch_size=max(1, settings.auto_bom_backfill_batch_size),
            )
            await session.commit()
            result.job_id = job.id
            result.claimed_items = len(claimed)

        try:
            batches = self._chunk_queue_items(claimed)
            total_batches = len(batches)
            total_sync_result = SyncResult()

            for batch_index, batch_items in enumerate(batches, start=1):
                async with self.session_factory() as session:
                    queue_repo = BomBackfillQueueRepo(session)
                    job = await session.get(SyncJobLog, result.job_id)
                    service = BomSyncService(session, SapBomClient(base_url=sap_bom_base_url))
                    live_items = await queue_repo.find_by_ids(
                        [queue_item.id for queue_item in batch_items if queue_item.id is not None]
                    )
                    for queue_item in batch_items:
                        if queue_item.id is None:
                            continue
                        live_item = live_items.get(queue_item.id)
                        if not live_item:
                            continue
                        execution = await service.sync_item(live_item.material_no, live_item.plant)
                        result.processed_items += 1
                        if execution.success:
                            result.success_items += 1
                            total_sync_result.success_count += execution.inserted_rows
                            total_sync_result.insert_count += execution.inserted_rows
                        else:
                            total_sync_result.fail_count += 1
                            await self._apply_failure(session, live_item, execution, result.job_id)
                            if execution.error_kind == BomBackfillFailureKind.PERMANENT_ERROR.value:
                                result.failed_items += 1
                            else:
                                result.retry_wait_items += 1

                    result.total_success_rows = total_sync_result.success_count
                    result.total_fail_rows = total_sync_result.fail_count
                    if job:
                        job.success_count = result.total_success_rows
                        job.fail_count = result.total_fail_rows
                        job.message = queue_consume_progress_message(
                            batch_current=batch_index,
                            batch_total=total_batches,
                            claimed_items=result.claimed_items,
                            processed_items=result.processed_items,
                            success_items=result.success_items,
                            retry_wait_items=result.retry_wait_items,
                            failed_items=result.failed_items,
                        )
                    await session.commit()

                if batch_index < total_batches and settings.auto_bom_backfill_batch_pause_seconds > 0:
                    import asyncio

                    await asyncio.sleep(settings.auto_bom_backfill_batch_pause_seconds)

            async with self.session_factory() as session:
                job = await session.get(SyncJobLog, result.job_id)
                if job:
                    result.message = queue_consume_completed_message(
                        claimed_items=result.claimed_items,
                        processed_items=result.processed_items,
                        success_items=result.success_items,
                        retry_wait_items=result.retry_wait_items,
                        failed_items=result.failed_items,
                        total_success_rows=result.total_success_rows,
                        total_fail_rows=result.total_fail_rows,
                    )
                    await finish_sync_job(session, job, total_sync_result, result.message)
                    await session.commit()
            return result
        except Exception as exc:
            logger.exception("BOM backfill queue consume failed: %s", exc)
            async with self.session_factory() as session:
                job = await session.get(SyncJobLog, result.job_id)
                if job:
                    fail_result = SyncResult(
                        success_count=result.total_success_rows,
                        fail_count=result.total_fail_rows + 1,
                        insert_count=result.total_success_rows,
                    )
                    fail_message = queue_consume_failed_message(exc)
                    await finish_sync_job(session, job, fail_result, fail_message)
                    await session.commit()
            result.message = queue_consume_failed_message(exc)
            return result

    async def list_queue_items(
        self,
        *,
        page_no: int,
        page_size: int,
        status: str | None = None,
        failure_kind: str | None = None,
        material_no: str | None = None,
        source: str | None = None,
    ) -> dict[str, Any]:
        async with self.session_factory() as session:
            repo = BomBackfillQueueRepo(session)
            total, items = await repo.list_page(
                page_no=page_no,
                page_size=page_size,
                status=status,
                failure_kind=failure_kind,
                material_no=material_no,
                source=source,
            )
            return {
                "total": total,
                "page_no": page_no,
                "page_size": page_size,
                "items": [serialize_bom_backfill_queue_item(item) for item in items],
            }

    async def retry_queue_items(self, ids: list[int]) -> int:
        if not ids:
            return 0
        async with self.session_factory() as session:
            stmt = select(BomBackfillQueue).where(BomBackfillQueue.id.in_(ids))
            items = (await session.execute(stmt)).scalars().all()
            changed = 0
            for item in items:
                if item.status not in {
                    BomBackfillQueueStatus.RETRY_WAIT.value,
                    BomBackfillQueueStatus.FAILED.value,
                }:
                    continue
                item.status = BomBackfillQueueStatus.PENDING.value
                item.next_retry_at = None
                item.failure_kind = None
                item.last_error = None
                changed += 1
            await session.commit()
            return changed

    async def _upsert_queue_item(
        self,
        *,
        session: AsyncSession,
        entity: BomBackfillQueue | None,
        material_no: str,
        plant: str,
        source: str,
        reason: str,
    ) -> str:
        now = utc_now()
        if entity is None:
            session.add(
                BomBackfillQueue(
                    material_no=material_no,
                    plant=plant,
                    source=source,
                    trigger_reason=reason,
                    status=BomBackfillQueueStatus.PENDING.value,
                    priority=100,
                    first_detected_at=now,
                )
            )
            await session.flush()
            return "enqueued"

        entity.source = source
        entity.trigger_reason = reason
        entity.priority = min(entity.priority or 100, 100)

        if entity.status in {
            BomBackfillQueueStatus.FAILED.value,
            BomBackfillQueueStatus.RETRY_WAIT.value,
            BomBackfillQueueStatus.SUCCESS.value,
        }:
            entity.status = BomBackfillQueueStatus.PENDING.value
            entity.fail_count = 0
            entity.next_retry_at = None
            entity.failure_kind = None
            entity.last_error = None
            entity.resolved_at = None
            entity.last_job_id = None
            await session.flush()
            return "reactivated"

        await session.flush()
        return "already_tracked"

    async def _load_candidates(
        self,
        session: AsyncSession,
        order_line_ids: list[int] | None,
    ) -> dict[str, list]:
        if order_line_ids is not None and len(order_line_ids) == 0:
            return {"order_ids": [], "items": []}
        normalized_order_plant = func.coalesce(
            SalesPlanOrderLineSrc.delivery_plant,
            literal("1000"),
        )
        normalized_bom_plant = func.coalesce(
            BomRelationSrc.plant,
            literal("1000"),
        )
        base_conditions = [
            SalesPlanOrderLineSrc.confirmed_delivery_date.is_not(None),
            SalesPlanOrderLineSrc.drawing_released == True,
            SalesPlanOrderLineSrc.material_no.is_not(None),
            ~exists(
                select(literal(1)).where(
                    BomRelationSrc.machine_material_no == SalesPlanOrderLineSrc.material_no,
                    normalized_bom_plant == normalized_order_plant,
                )
            ),
        ]
        if order_line_ids:
            base_conditions.append(SalesPlanOrderLineSrc.id.in_(order_line_ids))

        candidate_stmt = (
            select(
                SalesPlanOrderLineSrc.id,
                SalesPlanOrderLineSrc.material_no,
                normalized_order_plant.label("plant"),
            )
            .where(*base_conditions)
            .order_by(SalesPlanOrderLineSrc.id.asc())
        )

        rows = (await session.execute(candidate_stmt)).all()
        order_ids: set[int] = set()
        unique_items: set[tuple[str, str]] = set()
        for order_id, material_no, plant in rows:
            if order_id is not None:
                order_ids.add(int(order_id))
            if material_no:
                unique_items.add((str(material_no), str(plant)))

        return {
            "order_ids": sorted(order_ids),
            "items": sorted(unique_items, key=lambda item: (item[0], item[1])),
        }

    async def _apply_failure(
        self,
        session: AsyncSession,
        queue_item: BomBackfillQueue,
        execution: BomSyncExecutionResult,
        job_id: int | None,
    ) -> None:
        queue_item.fail_count += 1
        queue_item.last_job_id = job_id
        queue_item.failure_kind = execution.error_kind
        queue_item.last_error = execution.error_message

        if execution.error_kind == BomBackfillFailureKind.PERMANENT_ERROR.value:
            queue_item.status = BomBackfillQueueStatus.FAILED.value
            queue_item.next_retry_at = None
            await session.flush()
            return

        if queue_item.fail_count >= settings.bom_backfill_max_fail_count:
            queue_item.status = BomBackfillQueueStatus.FAILED.value
            queue_item.next_retry_at = None
            await session.flush()
            return

        queue_item.status = BomBackfillQueueStatus.RETRY_WAIT.value
        queue_item.next_retry_at = self._compute_next_retry_at(
            fail_count=queue_item.fail_count,
            error_kind=execution.error_kind,
        )
        await session.flush()

    @staticmethod
    def _chunk_queue_items(items: list[BomBackfillQueue]) -> list[list[BomBackfillQueue]]:
        batch_size = max(1, settings.auto_bom_backfill_batch_size)
        return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]

    @staticmethod
    def _compute_next_retry_at(*, fail_count: int, error_kind: str | None) -> datetime:
        now = utc_now()
        if error_kind == BomBackfillFailureKind.EMPTY_RESULT.value:
            return now + timedelta(minutes=settings.bom_backfill_empty_result_retry_minutes)

        base = max(1, settings.bom_backfill_retry_base_minutes)
        if fail_count <= 1:
            minutes = base
        elif fail_count == 2:
            minutes = base * 3
        elif fail_count == 3:
            minutes = base * 12
        elif fail_count == 4:
            minutes = base * 36
        else:
            minutes = base * 144
        return now + timedelta(minutes=minutes)
