from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, Field


class ScheduleListFilter(BaseModel):
    """排产列表筛选条件。"""

    page_no: int = Field(default=1, description="页码，从 1 开始。")
    page_size: int = Field(default=20, description="每页条数。")
    contract_no: Optional[str] = Field(default=None, description="合同号关键字。")
    customer_name: Optional[str] = Field(default=None, description="客户名称关键字。")
    product_series: Optional[str] = Field(default=None, description="产品系列。")
    product_model: Optional[str] = Field(default=None, description="机型。")
    order_no: Optional[str] = Field(default=None, description="销售订单号。")
    schedule_status: Optional[str] = Field(default=None, description="排产状态。")
    schedule_bucket: Optional[str] = Field(default=None, description="排产桶筛选，如 unscheduled / risk。")
    warning_level: Optional[str] = Field(default=None, description="预警等级。")
    drawing_released: Optional[bool] = Field(default=None, description="是否已发图。")
    date_from: Optional[str] = Field(default=None, description="日期范围开始，格式 yyyy-MM-dd。")
    date_to: Optional[str] = Field(default=None, description="日期范围结束，格式 yyyy-MM-dd。")


class ScheduleListItem(BaseModel):
    """整机排产列表项。"""

    order_line_id: int
    contract_no: Optional[str] = None
    customer_name: Optional[str] = None
    product_series: Optional[str] = None
    product_model: Optional[str] = None
    material_no: Optional[str] = None
    plant: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[Decimal] = None
    order_type: Optional[str] = None
    line_total_amount: Optional[Decimal] = None
    order_date: Optional[datetime] = None
    business_group: Optional[str] = None
    custom_no: Optional[str] = None
    sales_person_name: Optional[str] = None
    sales_branch_company: Optional[str] = None
    sales_sub_branch: Optional[str] = None
    order_no: Optional[str] = None
    sap_code: Optional[str] = None
    sap_line_no: Optional[str] = None
    confirmed_delivery_date: Optional[datetime] = None
    drawing_released: Optional[bool] = None
    drawing_release_date: Optional[datetime] = None
    custom_requirement: Optional[str] = None
    review_comment: Optional[str] = None
    trigger_date: Optional[datetime] = Field(default=None, description="排产触发日期；当前口径等同基于确认交期和整机主周期倒排出的最晚开工日。")
    machine_cycle_days: Optional[Decimal] = Field(default=None, description="整机主周期（天）；用于倒排 trigger_date / planned_start_date。")
    machine_assembly_days: Optional[Decimal] = Field(default=None, description="整机总装时长（天）；用于零件排产阶段预留总装窗口。")
    planned_start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None
    warning_level: Optional[str] = None
    schedule_status: Optional[str] = None
    default_flags: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class PartScheduleItem(BaseModel):
    """零件排产明细项。"""

    id: int
    order_line_id: int
    contract_no: Optional[str] = None
    customer_name: Optional[str] = None
    product_series: Optional[str] = None
    product_model: Optional[str] = None
    product_name: Optional[str] = None
    material_no: Optional[str] = None
    plant: Optional[str] = None
    quantity: Optional[Decimal] = None
    order_type: Optional[str] = None
    custom_no: Optional[str] = None
    business_group: Optional[str] = None
    sales_person_name: Optional[str] = None
    sales_branch_company: Optional[str] = None
    sales_sub_branch: Optional[str] = None
    assembly_name: str
    order_no: Optional[str] = None
    production_sequence: int
    assembly_time_days: Optional[Decimal] = Field(default=None, description="部装装配时长（天）；用于部装组在零件排产中的倒排窗口。")
    parent_material_no: Optional[str] = None
    parent_name: Optional[str] = None
    node_level: Optional[int] = None
    bom_path: Optional[str] = None
    bom_path_key: Optional[str] = None
    part_material_no: Optional[str] = None
    part_name: Optional[str] = None
    part_raw_material_desc: Optional[str] = None
    is_key_part: Optional[bool] = None
    part_cycle_days: Optional[Decimal] = Field(default=None, description="单个零件周期（天）；表示该零件自身匹配到的周期基准。")
    part_cycle_is_default: Optional[bool] = None
    part_cycle_match_rule: Optional[str] = None
    key_part_material_no: Optional[str] = None
    key_part_name: Optional[str] = None
    key_part_raw_material_desc: Optional[str] = None
    key_part_cycle_days: Optional[Decimal] = Field(default=None, description="关键零件周期（天）；当前口径作为所在部装组倒排开工时间的锚点周期。")
    planned_start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None
    order_date: Optional[datetime] = None
    confirmed_delivery_date: Optional[datetime] = None
    line_total_amount: Optional[Decimal] = None
    default_flags: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class PartScheduleListItem(BaseModel):
    """零件排产列表项。"""

    id: int
    order_line_id: int
    contract_no: Optional[str] = None
    customer_name: Optional[str] = None
    product_series: Optional[str] = None
    product_model: Optional[str] = None
    product_name: Optional[str] = None
    material_no: Optional[str] = None
    plant: Optional[str] = None
    quantity: Optional[Decimal] = None
    order_type: Optional[str] = None
    custom_no: Optional[str] = None
    business_group: Optional[str] = None
    sales_person_name: Optional[str] = None
    sales_branch_company: Optional[str] = None
    sales_sub_branch: Optional[str] = None
    order_no: Optional[str] = None
    assembly_name: str
    production_sequence: int
    assembly_time_days: Optional[Decimal] = Field(default=None, description="部装装配时长（天）；用于部装组在零件排产中的倒排窗口。")
    parent_material_no: Optional[str] = None
    parent_name: Optional[str] = None
    node_level: Optional[int] = None
    bom_path: Optional[str] = None
    bom_path_key: Optional[str] = None
    part_material_no: Optional[str] = None
    part_name: Optional[str] = None
    part_raw_material_desc: Optional[str] = None
    is_key_part: Optional[bool] = None
    part_cycle_days: Optional[Decimal] = Field(default=None, description="单个零件周期（天）；表示该零件自身匹配到的周期基准。")
    part_cycle_is_default: Optional[bool] = None
    part_cycle_match_rule: Optional[str] = None
    key_part_material_no: Optional[str] = None
    key_part_name: Optional[str] = None
    key_part_raw_material_desc: Optional[str] = None
    key_part_cycle_days: Optional[Decimal] = Field(default=None, description="关键零件周期（天）；当前口径作为所在部装组倒排开工时间的锚点周期。")
    planned_start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None
    order_date: Optional[datetime] = None
    confirmed_delivery_date: Optional[datetime] = None
    line_total_amount: Optional[Decimal] = None
    warning_level: Optional[str] = None
    default_flags: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class IssueItem(BaseModel):
    """异常项。"""

    id: int
    issue_type: str
    issue_level: Optional[str] = None
    source_system: Optional[str] = None
    biz_key: Optional[str] = None
    order_line_id: Optional[int] = None
    material_no: Optional[str] = None
    custom_no: Optional[str] = None
    order_no: Optional[str] = None
    contract_no: Optional[str] = None
    issue_title: str
    issue_detail: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ScheduleDetailResponse(BaseModel):
    """排产详情响应。"""

    machine_schedule: ScheduleListItem
    part_schedules: list[PartScheduleItem]
    issues: list[IssueItem]


class DashboardSummaryCountItem(BaseModel):
    """Dashboard 计数项。"""

    key: str
    count: int


class DashboardTopAssemblyItem(BaseModel):
    """零件部装 Top 统计项。"""

    assembly_name: str
    count: int


class MachineDashboardSummary(BaseModel):
    """整机排产总览摘要。"""

    total_orders: int
    scheduled_orders: int
    unscheduled_orders: int
    abnormal_orders: int
    status_counts: list[DashboardSummaryCountItem]
    planned_end_month_counts: list[DashboardSummaryCountItem]
    planned_end_day_counts: list[DashboardSummaryCountItem] = Field(default_factory=list, description="按日汇总的计划完工订单数（±14 天）。")
    warning_orders: list[ScheduleListItem]


class PartDashboardSummary(BaseModel):
    """零件排产总览摘要。"""

    total_parts: int
    abnormal_parts: int
    warning_counts: list[DashboardSummaryCountItem]
    top_assemblies: list[DashboardTopAssemblyItem]


class DashboardTimeSummary(BaseModel):
    """时间窗口统计摘要。"""

    delivery_count: int
    unscheduled_count: int
    abnormal_count: int


class DashboardTrendPoint(BaseModel):
    """排产 / 交付趋势点。"""

    key: str = Field(description="趋势点唯一标识；日维度为 yyyy-MM-dd，周维度为周起始日期，月维度为 yyyy-MM。")
    label: str = Field(description="趋势点展示标签。")
    scheduled_count: int = Field(description="按计划开工日统计的排产数量。")
    delivery_count: int = Field(description="按确认交期统计的交付数量。")


class DashboardDeliveryTrendSummary(BaseModel):
    """Dashboard 排产 / 交付趋势摘要。"""

    day: list[DashboardTrendPoint] = Field(description="按日展示的排产 / 交付趋势。")
    week: list[DashboardTrendPoint] = Field(description="按周展示的排产 / 交付趋势。")
    month: list[DashboardTrendPoint] = Field(description="按月展示的排产 / 交付趋势。")


class DashboardBusinessGroupSummaryItem(BaseModel):
    """事业群订单聚合项。"""

    business_group: str = Field(description="事业群名称；空值会统一归一为“未分组”。")
    order_count: int = Field(description="该事业群下的整机订单数量。")
    total_amount: Decimal = Field(default=Decimal("0"), description="该事业群下的订单总金额。")


class DashboardOverviewResponse(BaseModel):
    """Dashboard 总览响应。"""

    machine_summary: MachineDashboardSummary
    part_summary: PartDashboardSummary
    today_summary: DashboardTimeSummary
    week_summary: DashboardTimeSummary
    month_summary: DashboardTimeSummary
    delivery_trends: DashboardDeliveryTrendSummary
    business_group_summary: list[DashboardBusinessGroupSummaryItem]
    abnormal_machine_orders: list[ScheduleListItem]
    delivery_risk_orders: list[ScheduleListItem]


class ScheduleCalendarDaySummary(BaseModel):
    """排产日历单日汇总。"""

    calendar_date: date
    delivery_order_count: int = 0
    delivery_quantity_sum: Decimal = Decimal("0")
    trigger_order_count: int = 0
    trigger_quantity_sum: Decimal = Decimal("0")
    planned_start_order_count: int = 0
    planned_start_quantity_sum: Decimal = Decimal("0")


class ScheduleCalendarOrderItem(BaseModel):
    """排产日历中的订单项。"""

    order_line_id: int
    contract_no: Optional[str] = None
    order_no: Optional[str] = None
    product_model: Optional[str] = None
    material_no: Optional[str] = None
    plant: Optional[str] = None
    quantity: Optional[Decimal] = None
    schedule_status: Optional[str] = None
    confirmed_delivery_date: Optional[datetime] = None
    trigger_date: Optional[datetime] = None
    planned_start_date: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ScheduleCalendarDayDetailResponse(BaseModel):
    """排产日历单日明细响应。"""

    summary: ScheduleCalendarDaySummary
    delivery_orders: list[ScheduleCalendarOrderItem]
    trigger_orders: list[ScheduleCalendarOrderItem]
    planned_start_orders: list[ScheduleCalendarOrderItem]
