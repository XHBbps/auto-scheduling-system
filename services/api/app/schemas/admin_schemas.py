from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class SyncSalesPlanRequest(BaseModel):
    """销售计划手动同步请求。"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_time": "2026-03-01T00:00:00",
                "end_time": "2026-03-23T23:59:59",
            }
        }
    )

    start_time: Optional[datetime] = Field(default=None, description="同步窗口开始时间；为空时按默认增量窗口执行。")
    end_time: Optional[datetime] = Field(default=None, description="同步窗口结束时间；为空时按默认增量窗口执行。")


class SyncBomRequest(BaseModel):
    """BOM 手动同步请求。"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"order_line_ids": [1001, 1002]},
                {"material_no": "A123456", "plant": "1000"},
            ]
        }
    )

    order_line_ids: Optional[list[int]] = Field(default=None, description="按销售订单行触发 BOM 同步。")
    material_no: Optional[str] = Field(default=None, description="直接指定要同步的整机物料号。")
    plant: Optional[str] = Field(default=None, description="直接指定物料所在工厂；当 material_no 非空时建议同时提供。")


class SyncResearchRequest(BaseModel):
    """研究所数据手动同步请求。"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"mode": "increment"},
                {"mode": "by_order_no", "order_no": "SO20260323001"},
            ]
        }
    )

    mode: str = Field(default="increment", description="同步模式：increment 表示增量同步，by_order_no 表示按订单号定向同步。")
    order_no: Optional[str] = Field(default=None, description="当 mode=by_order_no 时使用的订单号过滤条件。")


class SyncScheduleRequest(BaseModel):
    """同步调度器开关请求。"""

    enabled: Optional[bool] = Field(default=None, description="是否启用自动同步调度器；true 启用，false 停用。")


class BomBackfillQueueRetryRequest(BaseModel):
    """BOM 补数队列重试请求。"""

    ids: list[int] = Field(description="要重置为待重试状态的队列记录 ID 列表。")


class ScheduleRunRequest(BaseModel):
    """批量排产请求。"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {},
                {"order_line_ids": [101, 102, 103], "force_rebuild": True},
            ]
        }
    )

    order_line_ids: Optional[list[int]] = Field(default=None, description="指定要排产的订单行 ID 列表；为空时自动选择当前可排产订单。")
    force_rebuild: bool = Field(default=True, description="保留字段；当前版本默认强制重建。")


class SingleOrderPartScheduleRunRequest(BaseModel):
    """单订单零件排产请求。"""

    model_config = ConfigDict(json_schema_extra={"example": {"order_line_id": 101}})

    order_line_id: int = Field(description="要执行单订单零件排产的销售订单行 ID。")


class MachineCycleBaselineRequest(BaseModel):
    """整机周期基准保存请求。"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_series": "X7",
                "machine_model": "X7-500",
                "plant": "1000",
                "order_qty": 1,
                "cycle_days_median": 45,
                "sample_count": 12,
                "is_active": True,
                "remark": "人工校准基准",
            }
        }
    )

    product_series: Optional[str] = Field(default=None, description="产品系列；可为空。")
    machine_model: str = Field(description="机型。")
    order_qty: Decimal = Field(description="订单数量分档。")
    cycle_days_median: Decimal = Field(description="该数量分档对应的整机主周期中位数（天）；用于倒排 trigger_date / planned_start_date。")
    sample_count: int = Field(default=0, description="用于生成该基准的样本数量。")
    is_active: bool = Field(default=True, description="是否启用该基准。")
    remark: Optional[str] = Field(default=None, description="备注。")


class PartCycleBaselineRequest(BaseModel):
    """零件周期基准保存请求。"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "part_type": "车架",
                "material_desc": "车架总成",
                "machine_model": "X7-500",
                "plant": "1000",
                "ref_batch_qty": 10,
                "cycle_days": 12,
                "unit_cycle_days": 1.2,
                "cycle_source": "manual",
                "match_rule": "机型 + 工厂 + 零件类型",
                "confidence_level": "high",
                "is_default": False,
                "is_active": True,
                "remark": "首版人工维护",
            }
        }
    )

    id: Optional[int] = Field(default=None, description="记录 ID；编辑已有记录时可传。")
    part_type: Optional[str] = Field(default=None, description="零件类型；为空时会根据其他字段推断。")
    material_no: Optional[str] = Field(default=None, description="零件物料号。")
    material_desc: str = Field(description="零件物料描述。")
    core_part_name: Optional[str] = Field(default=None, description="核心零件名称。")
    machine_model: Optional[str] = Field(default=None, description="机型；零件周期基准按机型维度维护。")
    plant: Optional[str] = Field(default=None, description="工厂；为空时表示该机型下的通用工厂基准。")
    ref_batch_qty: Decimal = Field(description="参考批量。")
    cycle_days: Decimal = Field(description="周期天数，即该零件在参考批量下完成加工所需的工作日天数。")
    unit_cycle_days: Decimal = Field(description="单件周期天数，即每件零件的加工周期；当参考批量为 1 时等于周期天数。")
    cycle_source: Optional[str] = Field(default=None, description="周期来源。")
    match_rule: Optional[str] = Field(default=None, description="匹配规则说明。")
    confidence_level: Optional[str] = Field(default=None, description="可信度等级。")
    is_default: bool = Field(default=False, description="是否为默认基准。")
    is_active: bool = Field(default=True, description="是否启用该基准。")
    remark: Optional[str] = Field(default=None, description="备注。")


class AssemblyTimeRequest(BaseModel):
    """装配时长配置保存请求。"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "machine_model": "X7-500",
                "plant": "1000",
                "product_series": "X7",
                "assembly_name": "整机总装",
                "assembly_time_days": 3,
                "is_final_assembly": True,
                "production_sequence": 99,
                "is_default": False,
                "remark": "默认总装时长",
            }
        }
    )

    machine_model: str = Field(description="机型。")
    product_series: Optional[str] = Field(default=None, description="产品系列；可为空。")
    assembly_name: str = Field(description="部装名称。")
    assembly_time_days: Decimal = Field(description="部装装配时长（天）；整机总装记录也使用该字段，但会在排产结果中单独映射为 machine_assembly_days。")
    is_final_assembly: bool = Field(default=False, description="是否为整机总装。")
    production_sequence: int = Field(description="生产顺序，数字越小越靠前。")
    is_default: bool = Field(default=False, description="是否为默认时长记录。")
    remark: Optional[str] = Field(default=None, description="备注。")


class WorkCalendarItem(BaseModel):
    """单日工作日历项。"""

    calendar_date: date = Field(description="日期。")
    is_workday: bool = Field(description="是否为工作日。")
    remark: Optional[str] = Field(default=None, description="日历备注。")


class WorkCalendarBatchRequest(BaseModel):
    """工作日历批量保存请求。"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {"calendar_date": "2026-03-23", "is_workday": True, "remark": "正常工作日"},
                    {"calendar_date": "2026-03-24", "is_workday": False, "remark": "设备检修"},
                ]
            }
        }
    )

    items: list[WorkCalendarItem] = Field(description="要批量保存的日历项列表。")


class IdStatusResponse(BaseModel):
    """仅返回 ID 和状态的处理结果。"""

    id: int = Field(description="记录 ID。")
    status: str = Field(description="处理后的状态。")


class IdMachineModelResponse(BaseModel):
    """仅返回 ID 和机型。"""

    id: int = Field(description="记录 ID。")
    machine_model: str = Field(description="机型。")


class IdPartTypeResponse(BaseModel):
    """仅返回 ID 和零件类型。"""

    id: int = Field(description="记录 ID。")
    part_type: str = Field(description="零件类型。")
    material_no: Optional[str] = Field(default=None, description="实际保存的物料号字段值。")


class ScheduleRunResponse(BaseModel):
    """批量排产返回结果。"""

    run_batch_no: Optional[str] = Field(default=None, description="本次排产批次号；没有可排产订单时为空。")
    total: int = Field(description="本次尝试排产的订单总数。")
    success_count: int = Field(description="排产成功数量。")
    fail_count: int = Field(description="排产失败数量。")
    message: Optional[str] = Field(default=None, description="附加说明。")


class ValidationItem(BaseModel):
    """单订单零件排产校验项。"""

    model_config = ConfigDict(extra="allow")

    code: str = Field(description="校验项编码。")
    label: str = Field(description="校验项标签。")
    message: str = Field(description="校验说明。")
    level: str = Field(default="blocking", description="级别，如 blocking / warning。")


class SingleOrderPartScheduleRunResponse(BaseModel):
    """单订单零件排产结果。"""

    order_line_id: int = Field(description="订单行 ID。")
    success: bool = Field(description="本次执行是否成功。")
    precheck_passed: bool = Field(description="前置校验是否通过。")
    status: str = Field(description="当前结果状态。")
    message: str = Field(description="结果说明。")
    validation_items: list[ValidationItem] = Field(default_factory=list, description="阻塞项或警告项列表。")
    machine_schedule_built: bool = Field(description="是否生成了整机排产结果。")
    part_schedule_built: bool = Field(description="是否生成了零件排产结果。")
    warning_summary: Optional[str] = Field(default=None, description="警告摘要。")
    assembly_count: Optional[int] = Field(default=None, description="识别到的部装数量。")
    part_candidate_count: Optional[int] = Field(default=None, description="识别到的零件候选数量。")
    check: Optional[dict[str, Any]] = Field(default=None, description="排产前检查详情。")


class SnapshotRefreshResult(BaseModel):
    """snapshot 刷新/重建结果。"""

    total: int = Field(description="总处理订单数。")
    refreshed: int = Field(description="已刷新快照数。")
    scheduled: int = Field(description="scheduled 状态数量。")
    scheduled_stale: int = Field(description="scheduled_stale 状态数量。")
    deleted: int = Field(description="被删除的快照数量。")


class SnapshotObservabilityResponse(BaseModel):
    """snapshot 观测摘要。"""

    model_config = ConfigDict(extra="allow")


class MachineCycleBaselineRebuildResponse(BaseModel):
    """整机周期基准重建结果。"""

    model_config = ConfigDict(extra="allow")


class SyncTriggerResponse(BaseModel):
    """手动同步触发结果。"""

    job_id: Optional[int] = Field(default=None, description="后台任务 ID；无任务时为空。")
    status: str = Field(description="任务状态，如 queued / running / noop。")
    message: str = Field(description="触发结果说明。")


class SyncSchedulerJobItem(BaseModel):
    """调度器任务项。"""

    id: str = Field(description="任务 ID。")
    name: str = Field(description="任务名称。")
    next_run_time: Optional[str] = Field(default=None, description="下次执行时间（ISO 格式）。")


class SyncSchedulerStatusResponse(BaseModel):
    """自动同步调度器状态。"""

    enabled: bool = Field(description="调度器是否处于启用状态。")
    state: str = Field(description="调度器状态，如 running / paused / stopped。")
    timezone: str = Field(description="调度器时区。")
    jobs: list[SyncSchedulerJobItem] = Field(default_factory=list, description="已注册任务列表。")


class SyncObservabilityResponse(BaseModel):
    """同步观测摘要。"""

    model_config = ConfigDict(extra="allow")


class BomBackfillQueueItemResponse(BaseModel):
    """BOM 补数队列项。"""

    model_config = ConfigDict(extra="allow")


class BomBackfillQueuePageResponse(BaseModel):
    """BOM 补数队列分页响应。"""

    total: int = Field(description="总记录数。")
    page_no: int = Field(description="当前页码。")
    page_size: int = Field(description="当前页大小。")
    items: list[BomBackfillQueueItemResponse] = Field(default_factory=list, description="队列记录列表。")


class RetryQueueResponse(BaseModel):
    """重置补数队列结果。"""

    updated_count: int = Field(description="已重置记录数。")
    message: str = Field(description="结果说明。")


class WorkCalendarRecordResponse(BaseModel):
    """工作日历记录。"""

    id: int = Field(description="记录 ID。")
    calendar_date: str = Field(description="日期，ISO 格式。")
    is_workday: bool = Field(description="是否工作日。")
    remark: Optional[str] = Field(default=None, description="备注。")


class WorkCalendarUpdateResponse(BaseModel):
    """工作日历更新结果。"""

    updated_count: int = Field(description="更新的日历记录数。")
    snapshot_refresh: SnapshotRefreshResult = Field(description="关联触发的 snapshot 刷新结果。")


class SyncLogItemResponse(BaseModel):
    """同步日志记录。"""

    model_config = ConfigDict(extra="allow")


class AssemblyTimeItemResponse(BaseModel):
    """装配时长配置项。"""

    id: int = Field(description="记录 ID。")
    machine_model: str = Field(description="机型。")
    product_series: Optional[str] = Field(default=None, description="产品系列。")
    assembly_name: str = Field(description="部装名称。")
    assembly_time_days: float = Field(description="部装装配时长（天）；整机总装记录也使用该字段，但会在排产结果中单独映射为 machine_assembly_days。")
    is_final_assembly: bool = Field(description="是否整机总装。")
    production_sequence: int = Field(description="生产顺序。")
    is_default: bool = Field(description="是否默认值。")
    remark: Optional[str] = Field(default=None, description="备注。")


class MachineCycleBaselineItemResponse(BaseModel):
    """整机周期基准项。"""

    id: int = Field(description="记录 ID。")
    product_series: Optional[str] = Field(default=None, description="产品系列。")
    machine_model: str = Field(description="机型。")
    order_qty: float = Field(description="订单数量分档。")
    cycle_days_median: float = Field(description="整机主周期中位数（天）；用于倒排 trigger_date / planned_start_date。")
    sample_count: int = Field(description="样本数量。")
    is_active: bool = Field(description="是否启用。")
    remark: Optional[str] = Field(default=None, description="备注。")


class PartCycleBaselineItemResponse(BaseModel):
    """零件周期基准项。"""

    id: int = Field(description="记录 ID。")
    part_type: str = Field(description="零件类型。")
    material_no: Optional[str] = Field(default=None, description="物料号。")
    material_desc: Optional[str] = Field(default=None, description="物料描述。")
    core_part_name: Optional[str] = Field(default=None, description="核心零件名称。")
    machine_model: Optional[str] = Field(default=None, description="机型。")
    plant: Optional[str] = Field(default=None, description="工厂。")
    ref_batch_qty: float = Field(description="参考批量。")
    cycle_days: float = Field(description="周期天数，参考批量下的加工工作日。")
    unit_cycle_days: float = Field(description="单件周期天数，每件零件的加工周期。")
    sample_count: int = Field(default=0, description="用于生成该基准的样本数量。")
    source_updated_at: Optional[str] = Field(default=None, description="源数据最近更新时间，ISO 格式。")
    cycle_source: Optional[str] = Field(default=None, description="周期来源。")
    match_rule: Optional[str] = Field(default=None, description="匹配规则。")
    confidence_level: Optional[str] = Field(default=None, description="可信度等级。")
    is_default: bool = Field(description="是否默认。")
    is_active: bool = Field(description="是否启用。")
    remark: Optional[str] = Field(default=None, description="备注。")
