from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from app.common.datetime_utils import utc_now
from app.common.enums import ScheduleStatus, WarningLevel
from app.models.data_issue import DataIssueRecord
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.data_issue_repo import DataIssueRepo
from app.repository.order_schedule_snapshot_repo import OrderScheduleSnapshotRepo
from app.scheduler.schedule_check_service import ScheduleCheckService
from app.services.schedule_snapshot_refresh_helpers import (
    build_issue_flags,
    build_order_payload,
    derive_warning_level,
    detect_scheduled_stale_reason,
    to_datetime,
)


class ScheduleSnapshotRefreshRefresher:
    """Single-snapshot refresh helpers for dynamic and machine-result paths."""

    def __init__(
        self,
        *,
        today: date,
        check_service: ScheduleCheckService,
        issue_repo: DataIssueRepo,
        snapshot_repo: OrderScheduleSnapshotRepo,
        schedule_affecting_fields: Sequence[str],
    ):
        self.today = today
        self.check_service = check_service
        self.issue_repo = issue_repo
        self.snapshot_repo = snapshot_repo
        self.schedule_affecting_fields = tuple(schedule_affecting_fields)

    async def refresh_from_dynamic_check(
        self,
        *,
        order: SalesPlanOrderLineSrc | None,
        source: str,
        reason: str,
        issues: Sequence[DataIssueRecord] | None = None,
        dynamic_context: dict[str, Any] | None = None,
        existing_snapshot: OrderScheduleSnapshot | None = None,
    ):
        if not order:
            return None

        if dynamic_context:
            check = await self.check_service.check_order(
                order,
                bom_material_pairs=dynamic_context["bom_material_pairs"],
                baselines_by_model=dynamic_context["baselines_by_model"],
                calendar=dynamic_context["calendar"],
            )
        else:
            check = await self.check_service.check(order.id)

        if issues is None:
            issues, _ = await self.issue_repo.paginate(
                page_no=1,
                page_size=100,
                order_line_id=order.id,
                status="open",
            )
        issues = list(issues)
        warning_level = derive_warning_level(
            schedule_status=check.get("status"),
            has_open_issues=bool(issues),
            fallback=WarningLevel.NORMAL,
        )
        default_flags: dict[str, Any] = {}
        if check.get("is_default_cycle"):
            default_flags["machine_cycle"] = True

        data = {
            **build_order_payload(order),
            "schedule_status": check.get("status") or ScheduleStatus.PENDING_DRAWING,
            "status_reason": check.get("reason") or reason,
            "trigger_date": to_datetime(check.get("trigger_date")),
            "machine_cycle_days": check.get("machine_cycle_days"),
            "is_default_cycle": bool(check.get("is_default_cycle")),
            "machine_schedule_id": None,
            "planned_start_date": None,
            "planned_end_date": None,
            "machine_assembly_days": None,
            "warning_level": warning_level,
            "default_flags": default_flags or None,
            "issue_flags": build_issue_flags(None, issues),
            "last_refresh_source": source,
            "refresh_reason": reason,
            "refreshed_at": utc_now(),
        }
        return await self.snapshot_repo.upsert_loaded_by_order_line_id(
            order.id,
            data,
            existing=existing_snapshot,
        )

    async def refresh_from_machine_result(
        self,
        *,
        order_line_id: int,
        order: SalesPlanOrderLineSrc | None,
        machine: MachineScheduleResult,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool,
        issues: Sequence[DataIssueRecord] | None = None,
        existing_snapshot: OrderScheduleSnapshot | None = None,
    ):
        if issues is None:
            issues, _ = await self.issue_repo.paginate(
                page_no=1,
                page_size=100,
                order_line_id=order_line_id,
                status="open",
            )
        issues = list(issues)
        base_status = machine.schedule_status or ScheduleStatus.SCHEDULED
        stale_reason = None
        if base_status == ScheduleStatus.SCHEDULED:
            if force_stale_for_scheduled:
                stale_reason = reason
            elif order:
                stale_reason = self.detect_scheduled_stale_reason(order, machine)
            schedule_status = ScheduleStatus.SCHEDULED_STALE if stale_reason else ScheduleStatus.SCHEDULED
        else:
            schedule_status = base_status

        warning_level = derive_warning_level(
            schedule_status=schedule_status,
            has_open_issues=bool(issues),
            fallback=machine.warning_level or WarningLevel.NORMAL,
        )
        data = {
            **build_order_payload(order or machine),
            "schedule_status": schedule_status,
            "status_reason": stale_reason or reason,
            "trigger_date": machine.trigger_date,
            "machine_cycle_days": machine.machine_cycle_days,
            "is_default_cycle": bool((machine.default_flags or {}).get("machine_cycle")),
            "machine_schedule_id": machine.id,
            "planned_start_date": machine.planned_start_date,
            "planned_end_date": machine.planned_end_date,
            "machine_assembly_days": machine.machine_assembly_days,
            "warning_level": warning_level,
            "default_flags": machine.default_flags,
            "issue_flags": build_issue_flags(machine.issue_flags, issues),
            "last_refresh_source": source,
            "refresh_reason": reason,
            "refreshed_at": utc_now(),
        }
        return await self.snapshot_repo.upsert_loaded_by_order_line_id(
            order_line_id,
            data,
            existing=existing_snapshot,
        )

    def detect_scheduled_stale_reason(
        self,
        order: SalesPlanOrderLineSrc,
        machine: MachineScheduleResult,
    ) -> str | None:
        return detect_scheduled_stale_reason(
            order,
            machine,
            self.schedule_affecting_fields,
        )
