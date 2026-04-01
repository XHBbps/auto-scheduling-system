
import logging
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.text_parse_utils import normalize_assembly_name
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.bom_relation_repo import BomRelationRepo
from app.repository.data_issue_repo import DataIssueRepo
from app.scheduler.machine_schedule_service import MachineScheduleService
from app.scheduler.part_schedule_service import PartScheduleService
from app.scheduler.schedule_check_service import ScheduleCheckService
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService
from app.scheduler.schedule_orchestrator_helpers import (
    build_final_assembly_time_default_issue_payload,
    build_machine_cycle_default_issue_payload,
    build_missing_bom_issue_payload,
    build_part_assembly_time_default_issue_payload,
    build_part_cycle_default_issue_payload,
    build_pending_delivery_issue_payload,
    build_pending_drawing_issue_payload,
    build_precheck_failure_response,
    build_validation_item,
    collect_schedule_warning_items,
    mark_machine_schedule_abnormal,
    mark_part_schedule_abnormal,
)

logger = logging.getLogger(__name__)


class ScheduleOrchestrator:
    def __init__(self, session: AsyncSession, today: date | None = None):
        self.session = session
        self.today = today or date.today()
        self.bom_repo = BomRelationRepo(session)
        self.issue_repo = DataIssueRepo(session)
        self.check_service = ScheduleCheckService(session, today=self.today)
        self.machine_service = MachineScheduleService(session, today=self.today)
        self.part_service = PartScheduleService(session)
        self.snapshot_refresh_service = ScheduleSnapshotRefreshService(session, today=self.today)

    @staticmethod
    def _build_validation_item(
        code: str,
        label: str,
        message: str,
        level: str = "blocking",
        **extra: Any,
    ) -> dict[str, Any]:
        return build_validation_item(
            code=code,
            label=label,
            message=message,
            level=level,
            **extra,
        )

    @classmethod
    def _build_precheck_failure_response(
        cls,
        order_line_id: int,
        status: str,
        message: str,
        validation_items: list[dict[str, Any]],
        check: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return build_precheck_failure_response(
            order_line_id=order_line_id,
            status=status,
            message=message,
            validation_items=validation_items,
            check=check,
        )

    async def validate_part_schedule_run(self, order_line_id: int) -> dict[str, Any]:
        order = await self.session.get(SalesPlanOrderLineSrc, order_line_id)
        if not order:
            return self._build_precheck_failure_response(
                order_line_id=order_line_id,
                status="not_found",
                message="未找到对应订单，无法发起零件排产。",
                validation_items=[
                    self._build_validation_item(
                        code="not_found",
                        label="订单数据",
                        message="订单不存在或已被删除。",
                    )
                ],
            )

        check = await self.check_service.check(order_line_id)
        if not check.get("is_schedulable"):
            validation_items: list[dict[str, Any]]
            status = check.get("status", "precheck_failed")
            if status == "pending_delivery":
                validation_items = [
                    self._build_validation_item(
                        code="missing_delivery_date",
                        label="状态确认",
                        message="缺少确认交货期，暂不允许发起零件排产。",
                    )
                ]
                message = "订单缺少确认交货期，零件排产校验未通过。"
            elif status == "pending_drawing":
                validation_items = [
                    self._build_validation_item(
                        code="pending_drawing",
                        label="状态确认",
                        message="发图状态未完成，暂不允许发起零件排产。",
                    )
                ]
                message = "订单尚未完成发图，零件排产校验未通过。"
            elif status == "missing_bom":
                validation_items = [
                    self._build_validation_item(
                        code="missing_bom",
                        label="BOM数据",
                        message="缺少整机 BOM 数据，暂不允许发起零件排产。",
                    )
                ]
                message = "订单缺少 BOM 数据，零件排产校验未通过。"
            elif status == "pending_trigger":
                trigger_date = check.get("trigger_date")
                trigger_text = trigger_date.isoformat() if trigger_date else "-"
                validation_items = [
                    self._build_validation_item(
                        code="pending_trigger",
                        label="状态确认",
                        message=f"未到排产触发日期（{trigger_text}），暂不允许发起零件排产。",
                    )
                ]
                message = "订单尚未达到排产触发条件，零件排产校验未通过。"
            else:
                validation_items = [
                    self._build_validation_item(
                        code=status,
                        label="状态确认",
                        message=check.get("reason", "当前订单不满足零件排产条件。"),
                    )
                ]
                message = "当前订单不满足零件排产条件。"

            return self._build_precheck_failure_response(
                order_line_id=order_line_id,
                status=status,
                message=message,
                validation_items=validation_items,
                check=check,
            )

        direct_children = await self.bom_repo.find_direct_children(
            order.material_no or "",
            order.delivery_plant,
        )
        assembly_component_nos: list[str] = []
        seen_assembly_components: set[str] = set()

        for bom_row in direct_children:
            if not normalize_assembly_name(bom_row.bom_component_desc or ""):
                continue
            component_no = bom_row.bom_component_no or ""
            if not component_no or component_no in seen_assembly_components:
                continue
            seen_assembly_components.add(component_no)
            assembly_component_nos.append(component_no)

        if not assembly_component_nos:
            return self._build_precheck_failure_response(
                order_line_id=order_line_id,
                status="missing_part_bom",
                message="BOM 中未识别到可用于零件排产的部装结构。",
                validation_items=[
                    self._build_validation_item(
                        code="missing_part_bom",
                        label="零件数据",
                        message="未识别到有效部装结构，请检查 BOM 层级和部装命名。",
                    )
                ],
            )

        part_candidate_count = 0
        recursive_self_made_parts_map = await self.part_service.key_part_service.list_recursive_self_made_parts_for_assemblies(
            machine_material_no=order.material_no or "",
            plant=order.delivery_plant,
            assemblies=[
                {
                    "assembly_name": normalize_assembly_name(bom_row.bom_component_desc or ""),
                    "bom_component_no": bom_row.bom_component_no,
                }
                for bom_row in direct_children
                if (bom_row.bom_component_no or "") in seen_assembly_components
            ],
        )
        for component_no in assembly_component_nos:
            part_candidate_count += len(recursive_self_made_parts_map.get(component_no, []))

        if part_candidate_count == 0:
            return self._build_precheck_failure_response(
                order_line_id=order_line_id,
                status="missing_part_data",
                message="部装下未识别到可排产的自制零件数据。",
                validation_items=[
                    self._build_validation_item(
                        code="missing_part_data",
                        label="零件数据",
                        message="部装下缺少可排产的自制零件，请检查零件 BOM 数据。",
                    )
                ],
            )

        return {
            "order_line_id": order_line_id,
            "success": True,
            "precheck_passed": True,
            "status": "schedulable",
            "message": "校验通过，可发起零件排产。",
            "validation_items": [],
            "machine_schedule_built": False,
            "part_schedule_built": False,
            "assembly_count": len(assembly_component_nos),
            "part_candidate_count": part_candidate_count,
            "check": check,
        }

    async def handle_part_schedule_precheck_failure(self, validation: dict[str, Any]) -> None:
        order_line_id = validation["order_line_id"]
        check = validation.get("check")
        if check:
            await self._record_precheck_issue(order_line_id, check)
        await self.snapshot_refresh_service.refresh_one(
            order_line_id,
            source="admin_schedule",
            reason=f"part_schedule_precheck_failed:{validation.get('status')}",
        )

    @classmethod
    def collect_schedule_warning_items(
        cls,
        machine_schedule: Any,
        part_schedules: list[Any],
    ) -> list[dict[str, Any]]:
        return collect_schedule_warning_items(
            cls._build_validation_item,
            machine_schedule,
            part_schedules,
        )

    async def schedule_order(self, order_line_id: int) -> dict[str, Any]:
        check = await self.check_service.check(order_line_id)
        if not check.get("is_schedulable"):
            await self._record_precheck_issue(order_line_id, check)
            await self.snapshot_refresh_service.refresh_one(
                order_line_id,
                source="schedule_orchestrator",
                reason=f"precheck_failed:{check.get('status')}",
            )
            return {
                "success": False,
                "order_line_id": order_line_id,
                "reason": check.get("reason", check.get("status")),
                "status": check.get("status"),
                "machine_schedule": None,
                "part_schedules": [],
            }

        machine_result = await self.machine_service.build(order_line_id)
        if not machine_result:
            await self.snapshot_refresh_service.refresh_one(
                order_line_id,
                source="schedule_orchestrator",
                reason="machine_schedule_build_failed",
            )
            return {
                "success": False,
                "order_line_id": order_line_id,
                "reason": "Failed to build machine schedule",
                "machine_schedule": None,
                "part_schedules": [],
            }

        await self._record_machine_schedule_default_issues(machine_result)
        part_results = await self.part_service.build(order_line_id, machine_result.id)
        await self._record_part_schedule_default_issues(machine_result, part_results)
        await self.snapshot_refresh_service.mark_scheduled(
            order_line_id,
            machine_schedule_id=machine_result.id,
            source="schedule_orchestrator",
            reason="schedule_success",
        )

        return {
            "success": True,
            "order_line_id": order_line_id,
            "machine_schedule": machine_result,
            "part_schedules": part_results,
        }

    async def _record_precheck_issue(
        self,
        order_line_id: int,
        check: dict[str, Any],
    ) -> None:
        status = check.get("status")
        if status == "missing_bom":
            await self._record_missing_bom_issue(order_line_id)
            return
        if status == "pending_delivery":
            await self._record_pending_delivery_issue(order_line_id)
            return
        if status == "pending_drawing":
            await self._record_pending_drawing_issue(order_line_id)

    @staticmethod
    def _mark_machine_schedule_abnormal(machine_schedule, flag_key: str) -> None:
        mark_machine_schedule_abnormal(machine_schedule, flag_key)

    @staticmethod
    def _mark_part_schedule_abnormal(part_schedule, flag_keys: list[str]) -> None:
        mark_part_schedule_abnormal(part_schedule, flag_keys)


    async def _record_missing_bom_issue(self, order_line_id: int) -> None:
        order = await self.session.get(SalesPlanOrderLineSrc, order_line_id)
        if not order:
            return
        await self.issue_repo.upsert_open_issue(**build_missing_bom_issue_payload(order_line_id, order))

    async def _record_pending_delivery_issue(self, order_line_id: int) -> None:
        order = await self.session.get(SalesPlanOrderLineSrc, order_line_id)
        if not order:
            return
        if not order.confirmed_delivery_date:
            await self.issue_repo.upsert_open_issue(**build_pending_delivery_issue_payload(order_line_id, order))

    async def _record_pending_drawing_issue(self, order_line_id: int) -> None:
        order = await self.session.get(SalesPlanOrderLineSrc, order_line_id)
        if not order:
            return
        if not order.drawing_released:
            await self.issue_repo.upsert_open_issue(**build_pending_drawing_issue_payload(order_line_id, order))

    async def _record_machine_schedule_default_issues(self, machine_schedule) -> None:
        default_flags = machine_schedule.default_flags or {}
        if default_flags.get("machine_cycle"):
            self._mark_machine_schedule_abnormal(machine_schedule, "machine_cycle_default")
            await self.issue_repo.upsert_open_issue(**build_machine_cycle_default_issue_payload(machine_schedule))

        if default_flags.get("final_assembly_time"):
            self._mark_machine_schedule_abnormal(machine_schedule, "final_assembly_time_default")
            await self.issue_repo.upsert_open_issue(**build_final_assembly_time_default_issue_payload(machine_schedule))

    async def _record_part_schedule_default_issues(self, machine_schedule, part_schedules) -> None:
        if not part_schedules:
            return

        assembly_defaults: list[str] = []
        cycle_defaults: list[str] = []

        for part_schedule in part_schedules:
            default_flags = dict(part_schedule.default_flags or {})
            if part_schedule.part_cycle_is_default:
                default_flags["part_cycle"] = True
            part_schedule.default_flags = default_flags or None

            abnormal_flags: list[str] = []
            if default_flags.get("assembly_time"):
                abnormal_flags.append("assembly_time_default")
                assembly_defaults.append(part_schedule.assembly_name)
            if default_flags.get("key_part_cycle"):
                abnormal_flags.append("key_part_cycle_default")
                cycle_defaults.append(
                    part_schedule.key_part_material_no or part_schedule.key_part_name or part_schedule.assembly_name
                )
            if default_flags.get("part_cycle"):
                abnormal_flags.append("part_cycle_default")
                cycle_defaults.append(
                    part_schedule.part_material_no or part_schedule.part_name or part_schedule.assembly_name
                )

            if abnormal_flags:
                self._mark_part_schedule_abnormal(part_schedule, abnormal_flags)
                self._mark_machine_schedule_abnormal(machine_schedule, "part_schedule_default")

        if assembly_defaults:
            await self.issue_repo.upsert_open_issue(**build_part_assembly_time_default_issue_payload(machine_schedule, assembly_defaults))

        if cycle_defaults:
            await self.issue_repo.upsert_open_issue(**build_part_cycle_default_issue_payload(machine_schedule, cycle_defaults))

    async def schedule_batch(self, order_line_ids: list[int]) -> dict[str, Any]:
        scheduled = 0
        failed = 0
        results = []

        for order_line_id in order_line_ids:
            try:
                async with self.session.begin_nested():
                    result = await self.schedule_order(order_line_id)
                if result["success"]:
                    scheduled += 1
                else:
                    failed += 1
                results.append(result)
            except Exception as exc:
                logger.error("Scheduling failed for order %s: %s", order_line_id, exc)
                failed += 1
                results.append({
                    "success": False,
                    "order_line_id": order_line_id,
                    "reason": str(exc),
                })

        return {
            "total": len(order_line_ids),
            "scheduled": scheduled,
            "failed": failed,
            "results": results,
        }
