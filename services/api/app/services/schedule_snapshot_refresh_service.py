import asyncio
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from time import perf_counter
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.datetime_utils import local_today, utc_now
from app.config import settings
from app.database import async_session_factory as default_async_session_factory
from app.models.data_issue import DataIssueRecord
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.data_issue_repo import DataIssueRepo
from app.repository.machine_schedule_result_repo import MachineScheduleResultRepo
from app.repository.order_schedule_snapshot_repo import OrderScheduleSnapshotRepo
from app.scheduler.schedule_check_service import ScheduleCheckService
from app.services.schedule_snapshot_refresh_action_helper import ScheduleSnapshotRefreshActionHelper
from app.services.schedule_snapshot_refresh_batch_helper import ScheduleSnapshotRefreshBatchHelper
from app.services.schedule_snapshot_refresh_context_loader import ScheduleSnapshotRefreshContextLoader
from app.services.schedule_snapshot_refresh_executor import ScheduleSnapshotRefreshExecutor
from app.services.schedule_snapshot_refresh_observability import (
    build_observability_summary,
    duration_ms,
    list_runtime_observations,
    record_runtime_observation,
    reset_runtime_observations,
)
from app.services.schedule_snapshot_refresh_refresher import ScheduleSnapshotRefreshRefresher
from app.services.schedule_snapshot_refresh_runtime_orchestrator import ScheduleSnapshotRefreshRuntimeOrchestrator
from app.services.schedule_snapshot_refresh_seed_helper import ScheduleSnapshotRefreshSeedHelper
from app.services.schedule_snapshot_refresh_seed_orchestrator import ScheduleSnapshotRefreshSeedOrchestrator
from app.services.schedule_snapshot_refresh_target_resolver import ScheduleSnapshotRefreshTargetResolver

_SCHEDULE_AFFECTING_FIELDS = (
    "confirmed_delivery_date",
    "drawing_released",
    "drawing_release_date",
    "material_no",
    "product_model",
    "quantity",
)
_SNAPSHOT_SEED_LOCAL_LOCK = asyncio.Lock()
_SNAPSHOT_SEED_ADVISORY_LOCK_KEY = 20260320


class ScheduleSnapshotRefreshService:
    def __init__(
        self,
        session: AsyncSession,
        today: date | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        self.session = session
        self.today = today or local_today()
        self.session_factory = session_factory or self._build_session_factory(session)
        self.snapshot_repo = OrderScheduleSnapshotRepo(session)
        self.machine_repo = MachineScheduleResultRepo(session)
        self.issue_repo = DataIssueRepo(session)
        self.check_service = ScheduleCheckService(session, today=self.today)
        self.context_loader = ScheduleSnapshotRefreshContextLoader(
            session=session,
            today=self.today,
            check_service=self.check_service,
            machine_repo=self.machine_repo,
            issue_repo=self.issue_repo,
        )
        self.action_helper = ScheduleSnapshotRefreshActionHelper()
        self.batch_helper = ScheduleSnapshotRefreshBatchHelper()
        self.executor = ScheduleSnapshotRefreshExecutor()
        self.seed_helper = ScheduleSnapshotRefreshSeedHelper(
            session=session,
            today=self.today,
        )
        self.seed_orchestrator = ScheduleSnapshotRefreshSeedOrchestrator()
        self.runtime_orchestrator = ScheduleSnapshotRefreshRuntimeOrchestrator(
            seed_lock=_SNAPSHOT_SEED_LOCAL_LOCK,
            advisory_lock_key=_SNAPSHOT_SEED_ADVISORY_LOCK_KEY,
        )
        self.refresher = ScheduleSnapshotRefreshRefresher(
            today=self.today,
            check_service=self.check_service,
            issue_repo=self.issue_repo,
            snapshot_repo=self.snapshot_repo,
            schedule_affecting_fields=_SCHEDULE_AFFECTING_FIELDS,
        )
        self.target_resolver = ScheduleSnapshotRefreshTargetResolver(
            session=session,
            seed_helper=self.seed_helper,
        )

    async def ensure_seeded(self, source: str = "system", reason: str = "snapshot_seed") -> bool:
        started_at = utc_now()
        started_perf = perf_counter()
        return await self.runtime_orchestrator.ensure_seeded(
            snapshot_exists_any=self.snapshot_repo.exists_any,
            ensure_seeded_committed=self._ensure_seeded_committed,
            record_runtime_observation=self._record_runtime_observation,
            duration_ms=self._duration_ms,
            source=source,
            reason=reason,
            started_at=started_at,
            started_perf=started_perf,
        )

    async def refresh_one(
        self,
        order_line_id: int,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool = False,
    ):
        return await self.executor.refresh_one(
            order_line_id=order_line_id,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
            find_snapshot=self.snapshot_repo.find_by_order_line_id,
            load_order=lambda item_id: self.session.get(SalesPlanOrderLineSrc, item_id),
            load_machine=self.machine_repo.find_by_order_line_id,
            delete_snapshot=self.snapshot_repo.delete_by_order_line_id,
            refresh_from_machine_result=self._refresh_from_machine_result,
            refresh_from_dynamic_check=self._refresh_from_dynamic_check,
        )

    async def refresh_one_committed(
        self,
        order_line_id: int,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool = False,
    ):
        started_at = utc_now()
        started_perf = perf_counter()
        return await self.runtime_orchestrator.refresh_one_committed(
            session_factory=self.session_factory,
            spawn_for_session=self._spawn_for_session,
            order_line_id=order_line_id,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
            record_runtime_observation=self._record_runtime_observation,
            duration_ms=self._duration_ms,
            started_at=started_at,
            started_perf=started_perf,
        )

    async def refresh_batch(
        self,
        order_line_ids: Iterable[int],
        source: str,
        reason: str,
        force_stale_for_scheduled: bool = False,
        shared_dynamic_context: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        return await self.executor.refresh_batch(
            order_line_ids=order_line_ids,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
            shared_dynamic_context=shared_dynamic_context,
            preload_refresh_batch_dependencies=self._preload_refresh_batch_dependencies,
            refresh_one_prefetched=self._refresh_one_prefetched,
        )

    async def refresh_by_material_no(
        self,
        material_no: str,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool = False,
    ) -> dict[str, int]:
        return await self.action_helper.refresh_by_material_no(
            material_no=material_no,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
            list_order_line_ids_by_material_no=self.target_resolver.list_order_line_ids_by_material_no,
            refresh_batch=self.refresh_batch,
        )

    async def refresh_by_product_model(
        self,
        product_model: str,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool = False,
    ) -> dict[str, int]:
        return await self.refresh_by_product_models(
            [product_model],
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
        )

    async def refresh_by_product_models(
        self,
        product_models: Sequence[str],
        source: str,
        reason: str,
        force_stale_for_scheduled: bool = False,
    ) -> dict[str, int]:
        return await self.action_helper.refresh_by_product_models(
            product_models=product_models,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
            list_order_line_ids_by_product_models=self.target_resolver.list_order_line_ids_by_product_models,
            refresh_batch=self.refresh_batch,
        )

    async def refresh_by_bom_component_no(
        self,
        bom_component_no: str,
        source: str,
        reason: str,
        machine_model: str | None = None,
        force_stale_for_scheduled: bool = False,
    ) -> dict[str, int]:
        return await self.action_helper.refresh_by_bom_component_no(
            bom_component_no=bom_component_no,
            source=source,
            reason=reason,
            machine_model=machine_model,
            force_stale_for_scheduled=force_stale_for_scheduled,
            list_order_line_ids_by_bom_component_no=self.target_resolver.list_order_line_ids_by_bom_component_no,
            refresh_batch=self.refresh_batch,
        )

    async def refresh_by_part_type(
        self,
        part_type: str,
        source: str,
        reason: str,
        machine_model: str | None = None,
        plant: str | None = None,
        force_stale_for_scheduled: bool = False,
    ) -> dict[str, int]:
        return await self.action_helper.refresh_by_part_type(
            part_type=part_type,
            source=source,
            reason=reason,
            machine_model=machine_model,
            plant=plant,
            force_stale_for_scheduled=force_stale_for_scheduled,
            list_order_line_ids_by_part_type=self.target_resolver.list_order_line_ids_by_part_type,
            refresh_batch=self.refresh_batch,
        )

    async def refresh_future_window(
        self,
        window_days: int | None,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool = False,
    ) -> dict[str, int]:
        started_at = utc_now()
        started_perf = perf_counter()
        return await self.runtime_orchestrator.refresh_future_window(
            resolve_target_ids=lambda days: self.target_resolver.list_order_line_ids_in_future_window(
                today=self.today,
                window_days=days,
            ),
            refresh_batch=self.refresh_batch,
            record_runtime_observation=self._record_runtime_observation,
            duration_ms=self._duration_ms,
            window_days=window_days,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
            started_at=started_at,
            started_perf=started_perf,
        )

    async def mark_scheduled(
        self,
        order_line_id: int,
        machine_schedule_id: int | None,
        source: str,
        reason: str,
    ):
        return await self.action_helper.mark_scheduled(
            order_line_id=order_line_id,
            machine_schedule_id=machine_schedule_id,
            source=source,
            reason=reason,
            refresh_one=self.refresh_one,
            load_machine_schedule=lambda schedule_id: self.session.get(MachineScheduleResult, schedule_id),
            flush=self.session.flush,
        )

    async def _refresh_one_prefetched(
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
    ):
        return await self.executor.refresh_one_prefetched(
            order_line_id=order_line_id,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
            order=order,
            machine=machine,
            issues=issues,
            existing_snapshot=existing_snapshot,
            dynamic_context=dynamic_context,
            delete_snapshot=self.snapshot_repo.delete_by_order_line_id,
            refresh_from_machine_result=self._refresh_from_machine_result,
            refresh_from_dynamic_check=self._refresh_from_dynamic_check,
        )

    async def mark_scheduled_stale(
        self,
        order_line_id: int,
        source: str,
        reason: str,
    ):
        return await self.action_helper.mark_scheduled_stale(
            order_line_id=order_line_id,
            source=source,
            reason=reason,
            refresh_one=self.refresh_one,
        )

    async def rebuild_all_open_snapshots(
        self,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool = False,
    ) -> dict[str, int]:
        started_at = utc_now()
        started_perf = perf_counter()
        return await self.runtime_orchestrator.rebuild_all_open_snapshots(
            rebuild_known_order_ids=self._refresh_all_known_order_line_ids_in_batches,
            record_runtime_observation=self._record_runtime_observation,
            duration_ms=self._duration_ms,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
            started_at=started_at,
            started_perf=started_perf,
        )

    async def get_observability_summary(self) -> dict[str, Any]:
        snapshot_aggregates = await self.snapshot_repo.get_observability_aggregates()
        return build_observability_summary(
            snapshot_aggregates=snapshot_aggregates,
            warn_refresh_age_minutes=settings.snapshot_observability_warn_refresh_age_minutes,
        )

    async def _ensure_seeded_committed(self, source: str, reason: str) -> bool:
        return await self.runtime_orchestrator.ensure_seeded_committed(
            session_factory=self.session_factory,
            spawn_for_session=self._spawn_for_session,
            source=source,
            reason=reason,
        )

    async def _acquire_seed_lock(self) -> None:
        await self.runtime_orchestrator.acquire_seed_lock(self.session)

    async def _fast_seed_all(self, source: str, reason: str) -> int:
        return await self.seed_orchestrator.fast_seed_all(
            session=self.session,
            source=source,
            reason=reason,
            iter_known_order_line_id_batches=self._iter_known_order_line_id_batches,
            build_shared_dynamic_context_for_known_orders=self._build_shared_dynamic_context_for_known_orders,
            preload_refresh_batch_dependencies=self._preload_refresh_batch_dependencies,
            build_seed_rows=self._build_seed_rows,
            bulk_upsert_snapshot_rows=self._bulk_upsert_snapshot_rows,
        )

    async def _refresh_from_dynamic_check(
        self,
        order: SalesPlanOrderLineSrc | None,
        source: str,
        reason: str,
        issues: Sequence[DataIssueRecord] | None = None,
        dynamic_context: dict[str, Any] | None = None,
        existing_snapshot: OrderScheduleSnapshot | None = None,
    ):
        return await self.refresher.refresh_from_dynamic_check(
            order=order,
            source=source,
            reason=reason,
            issues=issues,
            dynamic_context=dynamic_context,
            existing_snapshot=existing_snapshot,
        )

    async def _refresh_from_machine_result(
        self,
        order_line_id: int,
        order: SalesPlanOrderLineSrc | None,
        machine: MachineScheduleResult,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool,
        issues: Sequence[DataIssueRecord] | None = None,
        existing_snapshot: OrderScheduleSnapshot | None = None,
    ):
        return await self.refresher.refresh_from_machine_result(
            order_line_id=order_line_id,
            order=order,
            machine=machine,
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
            issues=issues,
            existing_snapshot=existing_snapshot,
        )

    async def _detect_scheduled_stale_reason(
        self,
        order: SalesPlanOrderLineSrc,
        machine: MachineScheduleResult,
    ) -> str | None:
        return self.refresher.detect_scheduled_stale_reason(order, machine)

    async def _list_all_known_order_line_ids(self) -> list[int]:
        return await self._list_known_order_line_id_batch()

    async def _list_order_line_ids_by_material_no(self, material_no: str) -> list[int]:
        return await self.target_resolver.list_order_line_ids_by_material_no(material_no)

    async def _preload_refresh_batch_dependencies(
        self,
        order_line_ids: Sequence[int],
        *,
        include_snapshot_map: bool = True,
        shared_dynamic_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.batch_helper.preload_refresh_batch_dependencies(
            order_line_ids=order_line_ids,
            include_snapshot_map=include_snapshot_map,
            shared_dynamic_context=shared_dynamic_context,
            load_sales_orders=self._load_sales_orders_by_order_line_ids,
            load_machine_results=self._load_machine_results_by_order_line_ids,
            load_open_issue_map=self._load_open_issue_map_for_order_line_ids,
            load_snapshots=self.snapshot_repo.find_by_order_line_ids,
            build_dynamic_context=self._build_dynamic_context,
        )

    async def _refresh_all_known_order_line_ids_in_batches(
        self,
        *,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool = False,
    ) -> dict[str, int]:
        return await self.batch_helper.refresh_all_known_order_line_ids_in_batches(
            source=source,
            reason=reason,
            force_stale_for_scheduled=force_stale_for_scheduled,
            build_shared_dynamic_context=self._build_shared_dynamic_context_for_known_orders,
            iter_known_order_line_id_batches=self._iter_known_order_line_id_batches,
            refresh_batch=self.refresh_batch,
            empty_refresh_batch_summary=self._empty_refresh_batch_summary,
            merge_refresh_batch_summary=self._merge_refresh_batch_summary,
        )

    async def _merge_order_line_ids(self, *stmts) -> list[int]:
        return await self.seed_helper.merge_order_line_ids(*stmts)

    @staticmethod
    def _normalize_order_line_id_stmt(stmt):
        return ScheduleSnapshotRefreshSeedHelper.normalize_order_line_id_stmt(stmt)

    async def _count_all_known_order_line_ids(self) -> int:
        return await self.seed_helper.count_all_known_order_line_ids()

    async def _list_known_order_line_id_batch(
        self,
        *,
        after_order_line_id: int | None = None,
        limit: int | None = None,
    ) -> list[int]:
        return await self.seed_helper.list_known_order_line_id_batch(
            after_order_line_id=after_order_line_id,
            limit=limit,
        )

    async def _iter_known_order_line_id_batches(self):
        async for batch in self.seed_helper.iter_known_order_line_id_batches(
            batch_size=self._snapshot_batch_size(),
        ):
            yield batch

    @staticmethod
    def _known_order_line_ids_subquery():
        return ScheduleSnapshotRefreshSeedHelper.known_order_line_ids_subquery()

    def _build_seed_rows(
        self,
        *,
        order_line_ids: Sequence[int],
        preloaded: dict[str, Any],
        source: str,
        reason: str,
    ) -> list[dict[str, Any]]:
        return self.seed_helper.build_seed_rows(
            order_line_ids=order_line_ids,
            preloaded=preloaded,
            source=source,
            reason=reason,
        )

    async def _bulk_upsert_snapshot_rows(self, rows: Sequence[dict[str, Any]]) -> None:
        await self.seed_helper.bulk_upsert_snapshot_rows(
            rows,
            batch_size=self._snapshot_batch_size(),
        )

    @staticmethod
    def _empty_refresh_batch_summary() -> dict[str, int]:
        return ScheduleSnapshotRefreshSeedHelper.empty_refresh_batch_summary()

    @classmethod
    def _merge_refresh_batch_summary(
        cls,
        current: dict[str, int],
        incoming: dict[str, int],
    ) -> dict[str, int]:
        return ScheduleSnapshotRefreshSeedHelper.merge_refresh_batch_summary(current, incoming)

    @staticmethod
    def _snapshot_batch_size() -> int:
        return max(int(settings.snapshot_refresh_batch_size or 0), 1)

    async def _load_sales_orders_by_order_line_ids(
        self,
        order_line_ids: Sequence[int],
    ) -> dict[int, SalesPlanOrderLineSrc]:
        return await self.context_loader.load_sales_orders_by_order_line_ids(order_line_ids)

    async def _load_machine_results_by_order_line_ids(
        self,
        order_line_ids: Sequence[int],
    ) -> dict[int, MachineScheduleResult]:
        return await self.context_loader.load_machine_results_by_order_line_ids(order_line_ids)

    async def _load_open_issue_map_for_order_line_ids(
        self,
        order_line_ids: Sequence[int],
    ) -> dict[int, list[DataIssueRecord]]:
        return await self.context_loader.load_open_issue_map_for_order_line_ids(order_line_ids)

    async def _load_open_issue_map(self) -> dict[int, list[DataIssueRecord]]:
        return await self.context_loader.load_open_issue_map()

    async def _load_machine_bom_pairs(self) -> set[tuple[str, str]]:
        return await self.context_loader.load_machine_bom_pairs()

    async def _build_dynamic_context(
        self,
        *,
        sales_orders: Sequence[SalesPlanOrderLineSrc],
        machine_rows: Sequence[MachineScheduleResult],
    ) -> dict[str, Any]:
        return await self.context_loader.build_dynamic_context(
            sales_orders=sales_orders,
            machine_rows=machine_rows,
        )

    async def _build_shared_dynamic_context_for_known_orders(self) -> dict[str, Any]:
        return await self.context_loader.build_shared_dynamic_context_for_known_orders()

    async def _load_machine_cycle_baselines(self) -> dict[str, list[MachineCycleBaseline]]:
        return await self.context_loader.load_machine_cycle_baselines()

    async def _load_seed_calendar(
        self,
        sales_orders: Sequence[SalesPlanOrderLineSrc],
        machine_rows: Sequence[MachineScheduleResult],
    ) -> dict[date, bool]:
        return await self.context_loader.load_seed_calendar(sales_orders, machine_rows)

    async def _load_known_order_max_delivery_date(self) -> date:
        return await self.context_loader.load_known_order_max_delivery_date()

    async def _load_calendar_until(self, end_date: date | datetime | None) -> dict[date, bool]:
        return await self.context_loader.load_calendar_until(end_date)

    @staticmethod
    def _normalize_date_value(value: date | datetime | None) -> date | None:
        return ScheduleSnapshotRefreshContextLoader.normalize_date_value(value)

    def _spawn_for_session(self, session: AsyncSession) -> "ScheduleSnapshotRefreshService":
        return ScheduleSnapshotRefreshService(
            session,
            today=self.today,
            session_factory=self.session_factory,
        )

    @staticmethod
    def _build_session_factory(
        session: AsyncSession,
    ) -> async_sessionmaker[AsyncSession]:
        bind = getattr(session, "bind", None)
        if bind is None:
            return default_async_session_factory
        return async_sessionmaker(bind, class_=AsyncSession, expire_on_commit=False)

    @classmethod
    def list_runtime_observations(cls) -> list[dict[str, Any]]:
        return list_runtime_observations()

    @classmethod
    def reset_runtime_observations(cls) -> None:
        reset_runtime_observations()

    @classmethod
    def _record_runtime_observation(
        cls,
        *,
        operation: str,
        source: str,
        reason: str,
        started_at: datetime,
        duration_ms: float,
        success: bool,
        summary: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        record_runtime_observation(
            operation=operation,
            source=source,
            reason=reason,
            started_at=started_at,
            duration_ms=duration_ms,
            success=success,
            summary=summary,
            error=error,
        )

    @staticmethod
    def _duration_ms(started_perf: float) -> float:
        return duration_ms(started_perf)
