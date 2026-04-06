from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.baseline.machine_cycle_baseline_service import MachineCycleBaselineService
from app.config import settings
from app.integration.feishu_client import FeishuClient
from app.integration.guandata_client import GuandataClient
from app.models.sync_job_log import SyncJobLog
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService
from app.sync.auto_bom_backfill_service import AutoBomBackfillResult, AutoBomBackfillService
from app.sync.drawing_status_sync_service import DrawingStatusSyncService
from app.sync.research_data_sync_service import ResearchSyncService
from app.sync.sales_plan_sync_service import SalesPlanSyncService
from app.sync.sync_job_message_templates import bom_missing_sap_message
from app.sync.sync_support_utils import SyncResult


@dataclass
class SyncWorkflowResult:
    sync_result: SyncResult
    drawing_updated_count: int = 0
    machine_cycle_baseline_rebuild: dict[str, Any] | None = None
    auto_bom_backfill: AutoBomBackfillResult | None = None


@dataclass
class DrawingRefreshResult:
    updated_ids: list[int]
    updated_count: int


class SyncWorkflowService:
    """Coordinate sync flows that require post-processing."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.snapshot_refresh_service = ScheduleSnapshotRefreshService(session)

    async def sync_sales_plan(
        self,
        client: GuandataClient,
        filters: dict[str, Any] | None = None,
        job: SyncJobLog | None = None,
    ) -> SyncWorkflowResult:
        service = SalesPlanSyncService(self.session, client)
        result = await service.sync(filters=filters, job=job)
        drawing_refresh = await self.refresh_drawing_status()
        await self.session.commit()
        auto_bom_backfill = await self.run_auto_bom_backfill(
            source="sales_plan_sync",
            reason="sales_plan_or_drawing_updated",
            order_line_ids=sorted(set(service.get_touched_order_line_ids()) | set(drawing_refresh.updated_ids)),
        )
        return SyncWorkflowResult(
            sync_result=result,
            drawing_updated_count=drawing_refresh.updated_count,
            auto_bom_backfill=auto_bom_backfill,
        )

    async def sync_research(
        self,
        client: FeishuClient,
        app_token: str,
        table_id: str,
        order_no_filter: str | None = None,
        job: SyncJobLog | None = None,
    ) -> SyncWorkflowResult:
        service = ResearchSyncService(
            self.session,
            client,
            app_token=app_token,
            table_id=table_id,
        )
        result = await service.sync(order_no_filter=order_no_filter, job=job)
        baseline_rebuild = await self.rebuild_machine_cycle_baselines(service.get_touched_product_models())
        await service.update_job_message(
            "整机周期基准重建："
            f"{baseline_rebuild.get('groups_processed', 0)}组 / "
            f"{baseline_rebuild.get('total_samples', 0)}条样本"
        )
        drawing_refresh = await self.refresh_drawing_status()
        await self.session.commit()
        auto_bom_backfill = await self.run_auto_bom_backfill(
            source="research_sync",
            reason="drawing_status_backfill",
            order_line_ids=drawing_refresh.updated_ids,
        )
        return SyncWorkflowResult(
            sync_result=result,
            drawing_updated_count=drawing_refresh.updated_count,
            machine_cycle_baseline_rebuild=baseline_rebuild,
            auto_bom_backfill=auto_bom_backfill,
        )

    async def refresh_drawing_status(self) -> DrawingRefreshResult:
        updated_ids = await DrawingStatusSyncService(self.session).refresh_all_with_ids()
        if updated_ids:
            await self.snapshot_refresh_service.refresh_batch(
                updated_ids,
                source="drawing_status_sync",
                reason="drawing_status_backfill",
            )
        return DrawingRefreshResult(
            updated_ids=updated_ids,
            updated_count=len(updated_ids),
        )

    async def run_auto_bom_backfill(
        self,
        *,
        source: str,
        reason: str,
        order_line_ids: list[int] | None = None,
    ) -> AutoBomBackfillResult:
        if not settings.sap_bom_base_url:
            return AutoBomBackfillResult(message=bom_missing_sap_message(source=source, reason=reason))
        return await AutoBomBackfillService().run(
            source=source,
            reason=reason,
            order_line_ids=order_line_ids,
            sap_bom_base_url=settings.sap_bom_base_url,
        )

    async def rebuild_machine_cycle_baselines(
        self,
        product_models: list[str] | None = None,
    ) -> dict[str, Any]:
        result = await MachineCycleBaselineService(self.session).rebuild()
        if product_models:
            await self.snapshot_refresh_service.refresh_by_product_models(
                product_models,
                source="research_sync",
                reason="machine_cycle_baseline_rebuilt",
            )
        else:
            await self.snapshot_refresh_service.rebuild_all_open_snapshots(
                source="research_sync",
                reason="machine_cycle_baseline_rebuilt",
            )
        return result
