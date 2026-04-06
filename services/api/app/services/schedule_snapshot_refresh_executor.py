from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Any

from app.common.enums import ScheduleStatus
from app.models.data_issue import DataIssueRecord
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc


class ScheduleSnapshotRefreshExecutor:
    """Execution helpers for single and batch snapshot refresh paths."""

    async def refresh_one(
        self,
        *,
        order_line_id: int,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool,
        find_snapshot: Callable[[int], Awaitable[OrderScheduleSnapshot | None]],
        load_order: Callable[[int], Awaitable[SalesPlanOrderLineSrc | None]],
        load_machine: Callable[[int], Awaitable[MachineScheduleResult | None]],
        delete_snapshot: Callable[[int], Awaitable[int]],
        refresh_from_machine_result: Callable[..., Awaitable[Any]],
        refresh_from_dynamic_check: Callable[..., Awaitable[Any]],
    ):
        existing_snapshot = await find_snapshot(order_line_id)
        order = await load_order(order_line_id)
        machine = await load_machine(order_line_id)

        if not order and not machine:
            if existing_snapshot:
                await delete_snapshot(order_line_id)
            return None

        if machine:
            return await refresh_from_machine_result(
                order_line_id=order_line_id,
                order=order,
                machine=machine,
                source=source,
                reason=reason,
                force_stale_for_scheduled=force_stale_for_scheduled,
                existing_snapshot=existing_snapshot,
            )

        return await refresh_from_dynamic_check(
            order=order,
            source=source,
            reason=reason,
            existing_snapshot=existing_snapshot,
        )

    async def refresh_one_prefetched(
        self,
        *,
        order_line_id: int,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool,
        order: SalesPlanOrderLineSrc | None,
        machine: MachineScheduleResult | None,
        issues: Sequence[DataIssueRecord],
        existing_snapshot: OrderScheduleSnapshot | None,
        dynamic_context: dict[str, Any] | None,
        delete_snapshot: Callable[[int], Awaitable[int]],
        refresh_from_machine_result: Callable[..., Awaitable[Any]],
        refresh_from_dynamic_check: Callable[..., Awaitable[Any]],
    ):
        if not order and not machine:
            if existing_snapshot:
                await delete_snapshot(order_line_id)
            return None

        if machine:
            return await refresh_from_machine_result(
                order_line_id=order_line_id,
                order=order,
                machine=machine,
                source=source,
                reason=reason,
                force_stale_for_scheduled=force_stale_for_scheduled,
                issues=issues,
                existing_snapshot=existing_snapshot,
            )

        return await refresh_from_dynamic_check(
            order=order,
            source=source,
            reason=reason,
            issues=issues,
            dynamic_context=dynamic_context,
            existing_snapshot=existing_snapshot,
        )

    async def refresh_batch(
        self,
        *,
        order_line_ids: Iterable[int],
        source: str,
        reason: str,
        force_stale_for_scheduled: bool,
        shared_dynamic_context: dict[str, Any] | None,
        preload_refresh_batch_dependencies: Callable[..., Awaitable[dict[str, Any]]],
        refresh_one_prefetched: Callable[..., Awaitable[Any]],
    ) -> dict[str, int]:
        refreshed = 0
        scheduled = 0
        scheduled_stale = 0
        deleted = 0
        seen = sorted({order_line_id for order_line_id in order_line_ids if order_line_id is not None})
        if not seen:
            return {
                "total": 0,
                "refreshed": 0,
                "scheduled": 0,
                "scheduled_stale": 0,
                "deleted": 0,
            }

        preloaded = await preload_refresh_batch_dependencies(
            seen,
            shared_dynamic_context=shared_dynamic_context,
        )
        dynamic_context = preloaded.get("dynamic_context")

        for order_line_id in seen:
            snapshot = await refresh_one_prefetched(
                order_line_id=order_line_id,
                source=source,
                reason=reason,
                force_stale_for_scheduled=force_stale_for_scheduled,
                order=preloaded["order_map"].get(order_line_id),
                machine=preloaded["machine_map"].get(order_line_id),
                issues=preloaded["issue_map"].get(order_line_id, []),
                existing_snapshot=preloaded["snapshot_map"].get(order_line_id),
                dynamic_context=dynamic_context,
            )
            if snapshot is None:
                deleted += 1
                continue
            refreshed += 1
            if snapshot.schedule_status == ScheduleStatus.SCHEDULED:
                scheduled += 1
            if snapshot.schedule_status == ScheduleStatus.SCHEDULED_STALE:
                scheduled_stale += 1

        return {
            "total": len(seen),
            "refreshed": refreshed,
            "scheduled": scheduled,
            "scheduled_stale": scheduled_stale,
            "deleted": deleted,
        }
