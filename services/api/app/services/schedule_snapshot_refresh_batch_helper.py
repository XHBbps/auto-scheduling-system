from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from app.models.machine_schedule_result import MachineScheduleResult
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc


class ScheduleSnapshotRefreshBatchHelper:
    """Batch preload and rebuild coordination helpers for snapshot refresh service."""

    async def preload_refresh_batch_dependencies(
        self,
        *,
        order_line_ids: Sequence[int],
        include_snapshot_map: bool,
        shared_dynamic_context: dict[str, Any] | None,
        load_sales_orders: Callable[[Sequence[int]], Awaitable[dict[int, SalesPlanOrderLineSrc]]],
        load_machine_results: Callable[[Sequence[int]], Awaitable[dict[int, MachineScheduleResult]]],
        load_open_issue_map: Callable[[Sequence[int]], Awaitable[dict[int, list[Any]]]],
        load_snapshots: Callable[[Sequence[int]], Awaitable[Sequence[OrderScheduleSnapshot]]],
        build_dynamic_context: Callable[..., Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        order_map = await load_sales_orders(order_line_ids)
        machine_map = await load_machine_results(order_line_ids)
        snapshot_map = (
            {snapshot.order_line_id: snapshot for snapshot in await load_snapshots(order_line_ids)}
            if include_snapshot_map
            else {}
        )
        issue_map = await load_open_issue_map(order_line_ids)

        dynamic_context = None
        if any(order_map.get(order_line_id) and not machine_map.get(order_line_id) for order_line_id in order_line_ids):
            dynamic_context = shared_dynamic_context or await build_dynamic_context(
                sales_orders=list(order_map.values()),
                machine_rows=list(machine_map.values()),
            )

        return {
            "order_map": order_map,
            "machine_map": machine_map,
            "snapshot_map": snapshot_map,
            "issue_map": issue_map,
            "dynamic_context": dynamic_context,
        }

    async def refresh_all_known_order_line_ids_in_batches(
        self,
        *,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool,
        build_shared_dynamic_context: Callable[[], Awaitable[dict[str, Any]]],
        iter_known_order_line_id_batches: Callable[[], Any],
        refresh_batch: Callable[..., Awaitable[dict[str, int]]],
        empty_refresh_batch_summary: Callable[[], dict[str, int]],
        merge_refresh_batch_summary: Callable[[dict[str, int], dict[str, int]], dict[str, int]],
    ) -> dict[str, int]:
        summary = empty_refresh_batch_summary()
        shared_dynamic_context = await build_shared_dynamic_context()
        async for order_line_ids in iter_known_order_line_id_batches():
            batch_result = await refresh_batch(
                order_line_ids,
                source=source,
                reason=reason,
                force_stale_for_scheduled=force_stale_for_scheduled,
                shared_dynamic_context=shared_dynamic_context,
            )
            summary = merge_refresh_batch_summary(summary, batch_result)
        return summary
