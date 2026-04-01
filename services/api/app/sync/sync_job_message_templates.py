from __future__ import annotations


def sales_plan_trigger_message(*, created: bool) -> str:
    return (
        "销售计划手动同步已触发，请稍后查看同步日志。"
        if created
        else "销售计划同步任务已在运行中，请查看当前任务日志。"
    )


def research_trigger_message(*, created: bool) -> str:
    return (
        "研究所数据手动同步已触发，请稍后查看同步日志。"
        if created
        else "研究所数据同步任务已在运行中，请查看当前任务日志。"
    )


def production_order_trigger_message(*, created: bool) -> str:
    return (
        "生产订单手动同步已触发，请稍后查看同步日志。"
        if created
        else "生产订单同步任务已在运行中，请查看当前任务日志。"
    )


def bom_trigger_message(*, created: bool) -> str:
    return (
        "BOM 手动同步已触发，请稍后查看同步日志。"
        if created
        else "BOM 同步任务已在运行中，请查看当前任务日志。"
    )


def bom_missing_sap_message(*, source: str, reason: str) -> str:
    return f"{source}:{reason} 跳过自动补 BOM：未配置 SAP BOM 接口地址。"


def sales_plan_result_message(
    *,
    success_count: int,
    fail_count: int,
    drawing_updated_count: int,
    enqueued_items: int,
    reactivated_items: int,
) -> str:
    return (
        f"销售计划同步完成：成功 {success_count} 条；失败 {fail_count} 条；"
        f"发图状态回填 {drawing_updated_count} 条；"
        f"自动补 BOM 入队 {enqueued_items} 个；重激活 {reactivated_items} 个。"
    )


def research_result_message(
    *,
    success_count: int,
    fail_count: int,
    drawing_updated_count: int,
    baseline_groups_processed: int,
    enqueued_items: int,
    reactivated_items: int,
) -> str:
    return (
        f"研究所数据同步完成：成功 {success_count} 条；失败 {fail_count} 条；"
        f"发图状态回填 {drawing_updated_count} 条；"
        f"整机周期基准重建 {baseline_groups_processed} 组；"
        f"自动补 BOM 入队 {enqueued_items} 个；重激活 {reactivated_items} 个。"
    )


def production_order_result_message(
    *,
    success_count: int,
    fail_count: int,
    baseline_rebuild_enqueued: int | None = None,
) -> str:
    message = f"生产订单同步完成：成功 {success_count} 条；失败 {fail_count} 条。"
    if baseline_rebuild_enqueued is None:
        return message
    if baseline_rebuild_enqueued > 0:
        return f"{message} 零件周期基准重建任务已入队 {baseline_rebuild_enqueued} 个。"
    return f"{message} 零件周期基准重建任务已存在活动任务，未重复入队。"


def bom_result_message(*, success_count: int, fail_count: int, item_count: int) -> str:
    return f"BOM 同步完成：成功 {success_count} 条；失败 {fail_count} 条；处理物料 {item_count} 个。"


def part_cycle_baseline_rebuild_result_message(
    *,
    eligible_groups: int,
    promoted_groups: int,
    persisted_groups: int,
    manual_protected_groups: int,
    deactivated_groups: int,
    snapshot_refreshed: int,
) -> str:
    return (
        "零件周期基准重建完成："
        f"符合条件 {eligible_groups} 组；"
        f"提升 {promoted_groups} 组；"
        f"落库 {persisted_groups} 组；"
        f"手工保护 {manual_protected_groups} 组；"
        f"停用 {deactivated_groups} 组；"
        f"刷新快照 {snapshot_refreshed} 条。"
    )


def auto_bom_enqueue_empty_message(*, source: str, reason: str) -> str:
    return f"{source}:{reason} 未发现需要自动补 BOM 的候选物料。"


def auto_bom_enqueue_summary_message(
    *,
    candidate_orders: int,
    candidate_items: int,
    enqueued_items: int,
    reactivated_items: int,
    already_tracked_items: int,
) -> str:
    return (
        "自动补齐 BOM 入队完成："
        f"候选订单 {candidate_orders} 条；"
        f"候选物料 {candidate_items} 个；"
        f"入队 {enqueued_items} 个；"
        f"重激活 {reactivated_items} 个；"
        f"已跟踪 {already_tracked_items} 个。"
    )


def queue_consume_running_message(*, source: str, reason: str, running_job_id: int) -> str:
    return f"{source}:{reason} 跳过 BOM 补数队列消费：同步任务 {running_job_id} 正在运行。"


def queue_consume_empty_message(*, source: str, reason: str) -> str:
    return f"{source}:{reason} 当前没有待消费的 BOM 补数队列项。"


def queue_consume_started_message(*, claimed_items: int, batch_size: int) -> str:
    return f"BOM 补数队列开始消费：认领 {claimed_items} 个；批大小 {batch_size}。"


def queue_consume_progress_message(
    *,
    batch_current: int,
    batch_total: int,
    claimed_items: int,
    processed_items: int,
    success_items: int,
    retry_wait_items: int,
    failed_items: int,
) -> str:
    return (
        "BOM 补数队列进行中："
        f"批次 {batch_current}/{batch_total}；"
        f"认领 {claimed_items} 个；"
        f"本轮处理 {processed_items} 个；"
        f"成功 {success_items} 个；"
        f"待重试 {retry_wait_items} 个；"
        f"永久失败 {failed_items} 个。"
    )


def queue_consume_completed_message(
    *,
    claimed_items: int,
    processed_items: int,
    success_items: int,
    retry_wait_items: int,
    failed_items: int,
    total_success_rows: int,
    total_fail_rows: int,
) -> str:
    return (
        "BOM 补数队列完成："
        f"认领 {claimed_items} 个；"
        f"本轮处理 {processed_items} 个；"
        f"成功 {success_items} 个；"
        f"待重试 {retry_wait_items} 个；"
        f"永久失败 {failed_items} 个；"
        f"BOM 行写入成功 {total_success_rows} 条；"
        f"失败 {total_fail_rows} 条。"
    )


def queue_consume_failed_message(exc: Exception) -> str:
    return f"BOM 补数队列消费失败：{exc}"
