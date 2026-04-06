import logging
from collections import deque
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import String, and_, cast, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utc_now
from app.common.enums import BomBackfillQueueStatus
from app.integration.sap_bom_client import SapBomClient
from app.models.bom_backfill_queue import BomBackfillQueue
from app.models.bom_relation import BomRelationSrc
from app.models.data_issue import DataIssueRecord
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.sync_job_log import SyncJobLog
from app.repository.bom_relation_repo import BomRelationRepo
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService
from app.sync.sync_support_utils import SyncResult, finish_sync_job, start_sync_job

logger = logging.getLogger(__name__)


def _compute_bom_levels(rows: list[dict[str, Any]], machine_material_no: str) -> list[dict[str, Any]]:
    children_of: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        parent = (row.get("material_no") or "").strip()
        if not parent:
            continue
        children_of.setdefault(parent, []).append(row)

    # Assign a stable index to each row for level tracking
    for idx, row in enumerate(rows):
        row["_row_idx"] = idx

    resolved_row_levels: dict[int, int] = {}
    parent_level_map: dict[str, int] = {machine_material_no: 0}
    queue: deque[str] = deque([machine_material_no])
    while queue:
        parent = queue.popleft()
        parent_level = parent_level_map[parent]
        for child in children_of.get(parent, []):
            child_level = parent_level + 1
            resolved_row_levels[child["_row_idx"]] = child_level

            child_material_no = (child.get("bom_component_no") or "").strip()
            if not child_material_no:
                continue
            existing_parent_level = parent_level_map.get(child_material_no)
            if existing_parent_level is None or child_level < existing_parent_level:
                parent_level_map[child_material_no] = child_level
                queue.append(child_material_no)

    for row in rows:
        row["bom_level"] = resolved_row_levels.get(row["_row_idx"], 1)
        row["is_top_level"] = row["bom_level"] == 1
        del row["_row_idx"]

    return rows


@dataclass
class BomSyncExecutionResult:
    machine_material_no: str
    plant: str
    success: bool
    inserted_rows: int = 0
    empty_result: bool = False
    error_kind: str | None = None
    error_message: str | None = None


_TRANSIENT_HTTP_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


def classify_bom_sync_exception(exc: Exception) -> tuple[str, str]:
    """Classify a BOM sync exception as transient (retryable) or permanent.

    Classification is based on exception types, not string matching:
    - httpx.HTTPStatusError with 408/429/5xx → transient
    - httpx.TimeoutException, httpx.RequestError → transient
    - ConnectionError, OSError → transient (network-level failures)
    - Everything else → permanent
    """
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code in _TRANSIENT_HTTP_STATUS_CODES:
            return "transient_error", str(exc)
        return "permanent_error", str(exc)
    if isinstance(exc, (httpx.TimeoutException, httpx.RequestError)):
        return "transient_error", str(exc)
    if isinstance(exc, (ConnectionError, OSError)):
        return "transient_error", str(exc)
    return "permanent_error", str(exc)


class BomSyncService:
    def __init__(self, session: AsyncSession, client: SapBomClient):
        self.session = session
        self.client = client
        self.repo = BomRelationRepo(session)
        self.snapshot_refresh_service = ScheduleSnapshotRefreshService(session)

    async def sync_item(
        self,
        machine_material_no: str,
        plant: str,
    ) -> BomSyncExecutionResult:
        try:
            raw_rows = await self.client.fetch_bom(machine_material_no, plant)
        except Exception as exc:
            logger.error("SAP BOM fetch failed for %s: %s", machine_material_no, exc)
            error_kind, error_message = classify_bom_sync_exception(exc)
            return BomSyncExecutionResult(
                machine_material_no=machine_material_no,
                plant=plant,
                success=False,
                error_kind=error_kind,
                error_message=error_message,
            )

        rows_with_levels = _compute_bom_levels(raw_rows, machine_material_no)
        if not rows_with_levels:
            return BomSyncExecutionResult(
                machine_material_no=machine_material_no,
                plant=plant,
                success=False,
                empty_result=True,
                error_kind="empty_result",
                error_message=f"SAP BOM returned empty result for {machine_material_no}/{plant}",
            )

        # Use savepoint so that if insert fails, the delete is rolled back
        # and existing BOM data is preserved.
        try:
            async with self.session.begin_nested():
                await self.repo.delete_by_machine_and_plant(machine_material_no, plant)

                entities = []
                for row in rows_with_levels:
                    entities.append(
                        BomRelationSrc(
                            machine_material_no=row["machine_material_no"],
                            machine_material_desc=row.get("machine_material_desc"),
                            plant=row.get("plant"),
                            material_no=row.get("material_no"),
                            bom_component_no=row["bom_component_no"],
                            bom_component_desc=row.get("bom_component_desc"),
                            part_type=row.get("part_type"),
                            component_qty=row.get("component_qty"),
                            bom_level=row.get("bom_level", 1),
                            is_top_level=row.get("is_top_level", False),
                            is_self_made=row.get("is_self_made", False),
                            sync_time=utc_now(),
                        )
                    )

                if entities:
                    await self.repo.add_all(entities)
        except Exception as exc:
            logger.error(
                "BOM replace failed for %s/%s, rolled back delete: %s",
                machine_material_no,
                plant,
                exc,
            )
            return BomSyncExecutionResult(
                machine_material_no=machine_material_no,
                plant=plant,
                success=False,
                error_kind="replace_failed",
                error_message=f"BOM delete+insert rolled back: {exc}",
            )

        await self.snapshot_refresh_service.refresh_by_material_no(
            machine_material_no,
            source="bom_sync",
            reason="bom_updated",
        )
        await self._close_missing_bom_issues(machine_material_no)
        await self._mark_queue_success(machine_material_no, plant)
        return BomSyncExecutionResult(
            machine_material_no=machine_material_no,
            plant=plant,
            success=True,
            inserted_rows=len(entities),
        )

    async def _sync_one(
        self,
        machine_material_no: str,
        plant: str,
        result: SyncResult,
    ) -> SyncResult:
        execution = await self.sync_item(machine_material_no, plant)
        if execution.success:
            result.success_count += execution.inserted_rows
            result.insert_count += execution.inserted_rows
        else:
            result.record_fail()
        return result

    async def sync_for_order(
        self,
        machine_material_no: str,
        plant: str,
        job: SyncJobLog | None = None,
    ) -> SyncResult:
        result = SyncResult()
        owns_job = job is None
        if owns_job:
            job = await start_sync_job(self.session, "bom", "sap")
            await self.session.commit()

        await self._sync_one(machine_material_no, plant, result)
        await finish_sync_job(self.session, job, result)
        return result

    async def sync_items(
        self,
        items: list[tuple[str, str]],
    ) -> SyncResult:
        total_result = SyncResult()
        for machine_material_no, plant in items:
            await self._sync_one(machine_material_no, plant, total_result)
        return total_result

    async def sync_batch(
        self,
        items: list[tuple[str, str]],
        job: SyncJobLog | None = None,
    ) -> SyncResult:
        if job is not None:
            total_result = await self.sync_items(items)
            await finish_sync_job(self.session, job, total_result)
            return total_result

        total_result = SyncResult()
        for machine_material_no, plant in items:
            result = await self.sync_for_order(machine_material_no, plant)
            total_result.success_count += result.success_count
            total_result.fail_count += result.fail_count
            total_result.insert_count += result.insert_count
        return total_result

    async def _close_missing_bom_issues(self, machine_material_no: str) -> None:
        order_id_subquery = select(cast(SalesPlanOrderLineSrc.id, String)).where(
            SalesPlanOrderLineSrc.material_no == machine_material_no
        )
        await self.session.execute(
            update(DataIssueRecord)
            .where(
                and_(
                    DataIssueRecord.issue_type == "BOM缺失",
                    DataIssueRecord.source_system == "scheduler",
                    DataIssueRecord.status == "open",
                    DataIssueRecord.biz_key.in_(order_id_subquery),
                )
            )
            .values(
                status="closed",
                handler="system",
                handled_at=utc_now(),
                remark="BOM sync resolved",
            )
        )
        await self.session.flush()

    async def _mark_queue_success(self, machine_material_no: str, plant: str) -> None:
        await self.session.execute(
            update(BomBackfillQueue)
            .where(
                BomBackfillQueue.material_no == machine_material_no,
                BomBackfillQueue.plant == plant,
            )
            .values(
                status=BomBackfillQueueStatus.SUCCESS.value,
                resolved_at=utc_now(),
                next_retry_at=None,
                failure_kind=None,
                last_error=None,
            )
        )
        await self.session.flush()
