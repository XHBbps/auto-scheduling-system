from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Sequence

from app.common.calendar_utils import subtract_workdays
from app.common.datetime_utils import utc_now
from app.common.enums import ScheduleStatus, WarningLevel
from app.common.plant_utils import normalize_plant
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.sales_plan import SalesPlanOrderLineSrc


def build_order_payload(source_obj: Any) -> dict[str, Any]:
    return {
        "contract_no": getattr(source_obj, "contract_no", None),
        "customer_name": getattr(source_obj, "customer_name", None),
        "product_series": getattr(source_obj, "product_series", None),
        "product_model": getattr(source_obj, "product_model", None),
        "product_name": getattr(source_obj, "product_name", None),
        "material_no": getattr(source_obj, "material_no", None),
        "plant": normalize_plant(
            getattr(source_obj, "delivery_plant", None) or getattr(source_obj, "plant", None)
        ),
        "quantity": getattr(source_obj, "quantity", None),
        "order_type": getattr(source_obj, "order_type", None),
        "line_total_amount": getattr(source_obj, "line_total_amount", None),
        "order_date": getattr(source_obj, "order_date", None),
        "business_group": getattr(source_obj, "business_group", None),
        "custom_no": getattr(source_obj, "custom_no", None),
        "sales_person_name": getattr(source_obj, "sales_person_name", None),
        "sales_branch_company": getattr(source_obj, "sales_branch_company", None),
        "sales_sub_branch": getattr(source_obj, "sales_sub_branch", None),
        "order_no": getattr(source_obj, "order_no", None),
        "sap_code": getattr(source_obj, "sap_code", None),
        "sap_line_no": getattr(source_obj, "sap_line_no", None),
        "confirmed_delivery_date": getattr(source_obj, "confirmed_delivery_date", None),
        "drawing_released": bool(getattr(source_obj, "drawing_released", False)),
        "drawing_release_date": getattr(source_obj, "drawing_release_date", None),
        "custom_requirement": getattr(source_obj, "custom_requirement", None),
        "review_comment": getattr(source_obj, "review_comment", None),
    }


def to_datetime(value: date | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min)


def build_issue_flags(base_flags: dict[str, Any] | None, issues: Sequence[Any]) -> dict[str, Any] | None:
    flags = dict(base_flags or {})
    if issues:
        flags["open_issues"] = True
        flags["open_issue_count"] = len(issues)
        flags["open_issue_types"] = sorted({issue.issue_type for issue in issues if getattr(issue, "issue_type", None)})
    return flags or None


def derive_warning_level(
    schedule_status: str | None,
    has_open_issues: bool,
    fallback: str,
) -> str:
    if has_open_issues or schedule_status in {ScheduleStatus.MISSING_BOM, ScheduleStatus.SCHEDULED_STALE}:
        return WarningLevel.ABNORMAL
    return fallback or WarningLevel.NORMAL


def normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.replace(microsecond=0)
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, Decimal):
        return value.normalize()
    return value


def get_machine_cycle_from_map(
    machine_model: str | None,
    quantity: Decimal | None,
    baselines_by_model: dict[str, list[MachineCycleBaseline]],
) -> tuple[Decimal, bool]:
    if not machine_model:
        return Decimal("90"), True

    qty = quantity or Decimal("1")
    baselines = baselines_by_model.get(machine_model) or []
    exact = next((baseline for baseline in baselines if baseline.order_qty == qty), None)
    if exact:
        return exact.cycle_days_median, False
    if baselines:
        nearest = min(baselines, key=lambda baseline: abs(baseline.order_qty - qty))
        coefficient = float(qty) / float(nearest.order_qty) if nearest.order_qty else 1.0
        adjusted = Decimal(str(round(float(nearest.cycle_days_median) * coefficient, 4)))
        return adjusted, False
    return Decimal("90"), True


def detect_scheduled_stale_reason(
    order: SalesPlanOrderLineSrc,
    machine: MachineScheduleResult,
    schedule_affecting_fields: Sequence[str],
) -> str | None:
    changed_fields = [
        field
        for field in schedule_affecting_fields
        if normalize_value(getattr(order, field, None))
        != normalize_value(getattr(machine, field, None))
    ]
    if changed_fields:
        return f"sales_plan_changed:{','.join(changed_fields)}"
    return None


def build_dynamic_snapshot_payload(
    *,
    today: date,
    order: SalesPlanOrderLineSrc,
    issues: Sequence[Any],
    source: str,
    reason: str,
    bom_material_pairs: set[tuple[str, str]],
    baselines_by_model: dict[str, list[MachineCycleBaseline]],
    calendar: dict[date, bool],
) -> dict[str, Any]:
    status: str
    status_reason: str
    trigger_date: datetime | None = None
    machine_cycle_days: Decimal | None = None
    is_default_cycle = False

    delivery = order.confirmed_delivery_date.date() if isinstance(order.confirmed_delivery_date, datetime) else order.confirmed_delivery_date
    if not delivery:
        status = ScheduleStatus.PENDING_DELIVERY
        status_reason = "No confirmed delivery date"
    elif not order.drawing_released:
        status = ScheduleStatus.PENDING_DRAWING
        status_reason = "Drawing not released"
    elif not order.material_no or (
        order.material_no,
        normalize_plant(getattr(order, "delivery_plant", None)),
    ) not in bom_material_pairs:
        status = ScheduleStatus.MISSING_BOM
        status_reason = "BOM not found"
    else:
        machine_cycle_days, is_default_cycle = get_machine_cycle_from_map(
            order.product_model,
            order.quantity,
            baselines_by_model,
        )
        trigger_date_only = subtract_workdays(delivery, int(machine_cycle_days), calendar)
        trigger_date = datetime.combine(trigger_date_only, time.min)
        if today < trigger_date_only:
            status = ScheduleStatus.PENDING_TRIGGER
            status_reason = "trigger_date_not_reached"
        else:
            status = ScheduleStatus.SCHEDULABLE
            status_reason = "schedulable"

    default_flags: dict[str, Any] = {}
    if is_default_cycle:
        default_flags["machine_cycle"] = True

    now = utc_now()
    return {
        "order_line_id": order.id,
        **build_order_payload(order),
        "schedule_status": status,
        "status_reason": status_reason,
        "trigger_date": trigger_date,
        "machine_cycle_days": machine_cycle_days,
        "is_default_cycle": bool(is_default_cycle),
        "machine_schedule_id": None,
        "planned_start_date": None,
        "planned_end_date": None,
        "machine_assembly_days": None,
        "warning_level": derive_warning_level(
            schedule_status=status,
            has_open_issues=bool(issues),
            fallback=WarningLevel.NORMAL,
        ),
        "default_flags": default_flags or None,
        "issue_flags": build_issue_flags(None, issues),
        "last_refresh_source": source,
        "refresh_reason": reason,
        "refreshed_at": now,
        "created_at": now,
        "updated_at": now,
    }


def build_machine_snapshot_payload(
    *,
    order_line_id: int,
    machine: MachineScheduleResult,
    order: SalesPlanOrderLineSrc | None,
    issues: Sequence[Any],
    source: str,
    reason: str,
    stale_reason: str | None,
) -> dict[str, Any]:
    base_status = machine.schedule_status or ScheduleStatus.SCHEDULED
    schedule_status = ScheduleStatus.SCHEDULED_STALE if stale_reason and base_status == ScheduleStatus.SCHEDULED else base_status
    now = utc_now()
    return {
        "order_line_id": order_line_id,
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
        "warning_level": derive_warning_level(
            schedule_status=schedule_status,
            has_open_issues=bool(issues),
            fallback=machine.warning_level or WarningLevel.NORMAL,
        ),
        "default_flags": machine.default_flags,
        "issue_flags": build_issue_flags(machine.issue_flags, issues),
        "last_refresh_source": source,
        "refresh_reason": reason,
        "refreshed_at": now,
        "created_at": now,
        "updated_at": now,
    }
