import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.machine_schedule_result_repo import MachineScheduleResultRepo
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService

logger = logging.getLogger(__name__)


class SalesPlanScheduleRefreshService:
    """Refresh snapshot truth source when sales-plan key fields change."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.machine_repo = MachineScheduleResultRepo(session)
        self.snapshot_refresh_service = ScheduleSnapshotRefreshService(session)

    async def refresh_if_scheduled(
        self,
        *,
        order_line_id: int,
        changed_fields: list[str],
    ) -> dict[str, Any]:
        existing_machine = await self.machine_repo.find_by_order_line_id(order_line_id)
        if not existing_machine:
            snapshot = await self.snapshot_refresh_service.refresh_one(
                order_line_id,
                source="sales_plan_sync",
                reason=f"sales_plan_changed:{','.join(changed_fields)}",
            )
            return {
                "triggered": False,
                "reason": "snapshot_refreshed_only",
                "order_line_id": order_line_id,
                "changed_fields": changed_fields,
                "snapshot_status": getattr(snapshot, "schedule_status", None),
            }

        logger.info(
            "Sales plan critical fields changed, mark scheduled snapshot stale: order_line_id=%s changed_fields=%s",
            order_line_id,
            changed_fields,
        )
        snapshot = await self.snapshot_refresh_service.mark_scheduled_stale(
            order_line_id,
            source="sales_plan_sync",
            reason=f"sales_plan_changed:{','.join(changed_fields)}",
        )
        return {
            "triggered": True,
            "order_line_id": order_line_id,
            "changed_fields": changed_fields,
            "snapshot_status": getattr(snapshot, "schedule_status", None),
            "stale_marked": bool(snapshot and snapshot.schedule_status == "scheduled_stale"),
        }
