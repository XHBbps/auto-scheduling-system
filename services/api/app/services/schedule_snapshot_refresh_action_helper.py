from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from app.common.enums import ScheduleStatus
from app.models.machine_schedule_result import MachineScheduleResult


class ScheduleSnapshotRefreshActionHelper:
    """Public action wrappers for snapshot refresh service."""

    async def refresh_by_material_no(
        self,
        *,
        material_no: str,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool,
        list_order_line_ids_by_material_no: Callable[[str], Awaitable[list[int]]],
        refresh_batch: Callable[..., Awaitable[dict[str, int]]],
    ) -> dict[str, int]:
        if not material_no:
            return {"total": 0, "refreshed": 0, "scheduled": 0, "scheduled_stale": 0, "deleted": 0}
        order_line_ids = await list_order_line_ids_by_material_no(material_no)
        return await refresh_batch(
            order_line_ids,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
        )

    async def refresh_by_product_models(
        self,
        *,
        product_models: Sequence[str],
        source: str,
        reason: str,
        force_stale_for_scheduled: bool,
        list_order_line_ids_by_product_models: Callable[[Sequence[str]], Awaitable[list[int]]],
        refresh_batch: Callable[..., Awaitable[dict[str, int]]],
    ) -> dict[str, int]:
        if not [model for model in dict.fromkeys(product_models) if model]:
            return {"total": 0, "refreshed": 0, "scheduled": 0, "scheduled_stale": 0, "deleted": 0}
        order_line_ids = await list_order_line_ids_by_product_models(product_models)
        return await refresh_batch(
            order_line_ids,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
        )

    async def refresh_by_bom_component_no(
        self,
        *,
        bom_component_no: str,
        source: str,
        reason: str,
        machine_model: str | None,
        force_stale_for_scheduled: bool,
        list_order_line_ids_by_bom_component_no: Callable[..., Awaitable[list[int]]],
        refresh_batch: Callable[..., Awaitable[dict[str, int]]],
    ) -> dict[str, int]:
        if not bom_component_no:
            return {"total": 0, "refreshed": 0, "scheduled": 0, "scheduled_stale": 0, "deleted": 0}
        order_line_ids = await list_order_line_ids_by_bom_component_no(
            bom_component_no,
            machine_model=machine_model,
        )
        return await refresh_batch(
            order_line_ids,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
        )

    async def refresh_by_part_type(
        self,
        *,
        part_type: str,
        source: str,
        reason: str,
        machine_model: str | None,
        plant: str | None,
        force_stale_for_scheduled: bool,
        list_order_line_ids_by_part_type: Callable[..., Awaitable[list[int]]],
        refresh_batch: Callable[..., Awaitable[dict[str, int]]],
    ) -> dict[str, int]:
        if not part_type:
            return {"total": 0, "refreshed": 0, "scheduled": 0, "scheduled_stale": 0, "deleted": 0}
        order_line_ids = await list_order_line_ids_by_part_type(
            part_type,
            machine_model=machine_model,
            plant=plant,
        )
        return await refresh_batch(
            order_line_ids,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
        )

    async def mark_scheduled(
        self,
        *,
        order_line_id: int,
        machine_schedule_id: int | None,
        source: str,
        reason: str,
        refresh_one: Callable[..., Awaitable[object | None]],
        load_machine_schedule: Callable[[int], Awaitable[MachineScheduleResult | None]],
        flush: Callable[[], Awaitable[None]],
    ):
        snapshot = await refresh_one(order_line_id, source=source, reason=reason)
        if snapshot and machine_schedule_id is not None:
            machine_schedule = await load_machine_schedule(machine_schedule_id)
            if machine_schedule and machine_schedule.order_line_id != order_line_id:
                raise ValueError("machine schedule result does not belong to the requested order_line_id")
            snapshot.machine_schedule_id = machine_schedule_id
            snapshot.schedule_status = ScheduleStatus.SCHEDULED
            snapshot.status_reason = reason
            await flush()
        return snapshot

    async def mark_scheduled_stale(
        self,
        *,
        order_line_id: int,
        source: str,
        reason: str,
        refresh_one: Callable[..., Awaitable[object | None]],
    ):
        return await refresh_one(
            order_line_id,
            source=source,
            reason=reason,
            force_stale_for_scheduled=True,
        )
