from typing import Any


def build_validation_item(
    code: str,
    label: str,
    message: str,
    level: str = "blocking",
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "code": code,
        "label": label,
        "message": message,
        "level": level,
    }
    payload.update(extra)
    return payload


def build_precheck_failure_response(
    order_line_id: int,
    status: str,
    message: str,
    validation_items: list[dict[str, Any]],
    check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "order_line_id": order_line_id,
        "success": False,
        "precheck_passed": False,
        "status": status,
        "message": message,
        "validation_items": validation_items,
        "machine_schedule_built": False,
        "part_schedule_built": False,
    }
    if check:
        payload["check"] = check
    return payload


def collect_schedule_warning_items(
    build_validation_item_fn,
    machine_schedule: Any,
    part_schedules: list[Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    def add_warning(code: str, label: str, message: str) -> None:
        if code in seen_codes:
            return
        seen_codes.add(code)
        items.append(
            build_validation_item_fn(
                code=code,
                label=label,
                message=message,
                level="warning",
            )
        )

    machine_default_flags = dict(getattr(machine_schedule, "default_flags", None) or {})
    if machine_default_flags.get("machine_cycle"):
        add_warning(
            "machine_cycle_default",
            "历史周期数据",
            "整机历史周期基准缺失，已按默认值完成排产。",
        )
    if machine_default_flags.get("final_assembly_time"):
        add_warning(
            "final_assembly_time_default",
            "装配时长",
            "整机总装时长基准缺失，已按默认值完成排产。",
        )

    part_default_flags = [dict(getattr(item, "default_flags", None) or {}) for item in part_schedules]
    if any(flags.get("assembly_time") for flags in part_default_flags):
        add_warning(
            "assembly_time_default",
            "装配时长",
            "部分部装装配时长基准缺失，已按默认值完成排产。",
        )
    if any(flags.get("key_part_cycle") for flags in part_default_flags):
        add_warning(
            "key_part_cycle_default",
            "历史周期数据",
            "部分关键零件周期基准缺失，已按默认值完成排产。",
        )
    if any(flags.get("part_cycle") for flags in part_default_flags):
        add_warning(
            "part_cycle_default",
            "历史周期数据",
            "部分零件周期基准缺失，已按默认值完成排产。",
        )

    return items


def mark_machine_schedule_abnormal(machine_schedule: Any, flag_key: str) -> None:
    machine_schedule.warning_level = "abnormal"
    issue_flags = dict(machine_schedule.issue_flags or {})
    issue_flags[flag_key] = True
    machine_schedule.issue_flags = issue_flags


def mark_part_schedule_abnormal(part_schedule: Any, flag_keys: list[str]) -> None:
    if not flag_keys:
        return
    part_schedule.warning_level = "abnormal"
    issue_flags = dict(part_schedule.issue_flags or {})
    for flag_key in flag_keys:
        issue_flags[flag_key] = True
    part_schedule.issue_flags = issue_flags


def summarize_items(items: list[str], limit: int = 5) -> str:
    unique_items: list[str] = []
    for item in items:
        if item and item not in unique_items:
            unique_items.append(item)
    if not unique_items:
        return "-"
    if len(unique_items) <= limit:
        return "、".join(unique_items)
    summary = "、".join(unique_items[:limit])
    return f"{summary} 等{len(unique_items)}项"


def build_missing_bom_issue_payload(order_line_id: int, order: Any) -> dict[str, Any]:
    return {
        "issue_type": "BOM缺失",
        "issue_level": "high",
        "source_system": "scheduler",
        "biz_key": str(order_line_id),
        "order_line_id": order_line_id,
        "issue_title": "排产前缺少 BOM 数据",
        "issue_detail": (
            f"订单行 {order_line_id} 缺少 BOM 数据；"
            f"order_no={order.order_no or '-'}；material_no={order.material_no or '-'}。"
        ),
    }


def build_pending_delivery_issue_payload(order_line_id: int, order: Any) -> dict[str, Any]:
    return {
        "issue_type": "确认交货期缺失",
        "issue_level": "medium",
        "source_system": "scheduler",
        "biz_key": str(order_line_id),
        "order_line_id": order_line_id,
        "issue_title": "排产前缺少确认交货期",
        "issue_detail": (
            f"订单行 {order_line_id} 缺少确认交货期；"
            f"order_no={order.order_no or '-'}；material_no={order.material_no or '-'}。"
        ),
    }


def build_pending_drawing_issue_payload(order_line_id: int, order: Any) -> dict[str, Any]:
    return {
        "issue_type": "发图状态未完成",
        "issue_level": "medium",
        "source_system": "scheduler",
        "biz_key": str(order_line_id),
        "order_line_id": order_line_id,
        "issue_title": "排产前发图状态未完成",
        "issue_detail": (
            f"订单行 {order_line_id} 未完成发图；"
            f"order_no={order.order_no or '-'}；material_no={order.material_no or '-'}。"
        ),
    }


def build_machine_cycle_default_issue_payload(machine_schedule: Any) -> dict[str, Any]:
    return {
        "issue_type": "整机周期基准缺失",
        "issue_level": "medium",
        "source_system": "scheduler",
        "biz_key": str(machine_schedule.order_line_id),
        "order_line_id": machine_schedule.order_line_id,
        "issue_title": "整机周期基准缺失，已按默认值排产",
        "issue_detail": (
            f"订单行 {machine_schedule.order_line_id} 缺少整机周期基准；"
            f"product_model={machine_schedule.product_model or '-'}；"
            f"material_no={machine_schedule.material_no or '-'}；已按默认 90 天排产。"
        ),
    }


def build_final_assembly_time_default_issue_payload(machine_schedule: Any) -> dict[str, Any]:
    return {
        "issue_type": "装配时长基准缺失",
        "issue_level": "medium",
        "source_system": "scheduler",
        "biz_key": str(machine_schedule.order_line_id),
        "order_line_id": machine_schedule.order_line_id,
        "issue_title": "装配时长基准缺失，已按默认值排产",
        "issue_detail": (
            f"订单行 {machine_schedule.order_line_id} 缺少整机总装时长基准；"
            f"product_model={machine_schedule.product_model or '-'}；"
            f"material_no={machine_schedule.material_no or '-'}；已按默认 3 天排产。"
        ),
    }


def build_part_assembly_time_default_issue_payload(machine_schedule: Any, assembly_defaults: list[str]) -> dict[str, Any]:
    return {
        "issue_type": "装配时长基准缺失",
        "issue_level": "medium",
        "source_system": "scheduler",
        "biz_key": str(machine_schedule.order_line_id),
        "order_line_id": machine_schedule.order_line_id,
        "issue_title": "装配时长基准缺失，已按默认值排产",
        "issue_detail": (
            f"订单行 {machine_schedule.order_line_id} 缺少部装时长基准；"
            f"涉及部装：{summarize_items(assembly_defaults)}；已按默认值排产。"
        ),
    }


def build_part_cycle_default_issue_payload(machine_schedule: Any, cycle_defaults: list[str]) -> dict[str, Any]:
    return {
        "issue_type": "零件周期基准缺失",
        "issue_level": "medium",
        "source_system": "scheduler",
        "biz_key": str(machine_schedule.order_line_id),
        "order_line_id": machine_schedule.order_line_id,
        "issue_title": "零件周期基准缺失，已按默认值排产",
        "issue_detail": (
            f"订单行 {machine_schedule.order_line_id} 缺少零件周期基准；"
            f"涉及物料：{summarize_items(cycle_defaults)}；已按默认值排产。"
        ),
    }
