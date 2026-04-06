from __future__ import annotations

from pydantic import BaseModel, Field


class SalesPlanOrgFilterOptionsResponse(BaseModel):
    """销售组织筛选项。"""

    business_groups: list[str] = Field(default_factory=list, description="事业部筛选项。")
    sales_branch_companies: list[str] = Field(default_factory=list, description="销售分公司筛选项。")
    sales_sub_branches: list[str] = Field(default_factory=list, description="销售子公司/办事处筛选项。")


class SalesPlanOrderItemResponse(BaseModel):
    """销售计划订单行。"""

    id: int = Field(description="记录 ID。")
    contract_no: str | None = Field(default=None, description="合同号。")
    customer_name: str | None = Field(default=None, description="客户名称。")
    product_series: str | None = Field(default=None, description="产品系列。")
    product_model: str | None = Field(default=None, description="机型。")
    product_name: str | None = Field(default=None, description="产品名称。")
    material_no: str | None = Field(default=None, description="物料号。")
    quantity: float | None = Field(default=None, description="数量。")
    line_total_amount: float | None = Field(default=None, description="行金额。")
    confirmed_delivery_date: str | None = Field(default=None, description="确认交期，ISO 格式。")
    delivery_date: str | None = Field(default=None, description="原始交期，ISO 格式。")
    order_type: str | None = Field(default=None, description="订单类型。")
    business_group: str | None = Field(default=None, description="事业部。")
    custom_no: str | None = Field(default=None, description="定制号。")
    sales_person_name: str | None = Field(default=None, description="销售人员。")
    order_date: str | None = Field(default=None, description="订单日期，ISO 格式。")
    sales_branch_company: str | None = Field(default=None, description="销售分公司。")
    sales_sub_branch: str | None = Field(default=None, description="销售子公司/办事处。")
    drawing_released: bool | None = Field(default=None, description="是否已发图。")
    drawing_release_date: str | None = Field(default=None, description="发图日期，ISO 格式。")
    order_no: str | None = Field(default=None, description="销售订单号。")
    sap_code: str | None = Field(default=None, description="SAP 编码。")
    sap_line_no: str | None = Field(default=None, description="SAP 行号。")
    custom_requirement: str | None = Field(default=None, description="定制要求。")
    review_comment: str | None = Field(default=None, description="评审备注。")
    created_at: str | None = Field(default=None, description="入库时间，ISO 格式。")


class BomRelationItemResponse(BaseModel):
    """BOM 明细记录。"""

    id: int = Field(description="记录 ID。")
    machine_material_no: str | None = Field(default=None, description="整机物料号。")
    machine_material_desc: str | None = Field(default=None, description="整机物料描述。")
    plant: str | None = Field(default=None, description="工厂。")
    material_no: str | None = Field(default=None, description="父级物料号。")
    material_desc: str | None = Field(default=None, description="父级物料描述。")
    bom_component_no: str | None = Field(default=None, description="子件物料号。")
    bom_component_desc: str | None = Field(default=None, description="子件物料描述。")
    part_type: str | None = Field(default=None, description="零件类型。")
    component_qty: float | None = Field(default=None, description="组件数量。")
    bom_level: int | None = Field(default=None, description="BOM 层级。")
    is_top_level: bool | None = Field(default=None, description="是否顶层。")
    is_self_made: bool | None = Field(default=None, description="是否自制件。")
    sync_time: str | None = Field(default=None, description="同步时间，ISO 格式。")
    created_at: str | None = Field(default=None, description="入库时间，ISO 格式。")


class BomTreeNodeResponse(BaseModel):
    """BOM 树节点。"""

    id: int = Field(description="节点 ID。")
    node_key: str = Field(description="前端树节点 key。")
    machine_material_no: str | None = Field(default=None, description="整机物料号。")
    plant: str | None = Field(default=None, description="工厂。")
    parent_material_no: str | None = Field(default=None, description="父级物料号。")
    parent_material_desc: str | None = Field(default=None, description="父级物料描述。")
    material_no: str | None = Field(default=None, description="当前节点物料号。")
    material_desc: str | None = Field(default=None, description="当前节点物料描述。")
    part_type: str | None = Field(default=None, description="零件类型。")
    component_qty: float | None = Field(default=None, description="组件数量。")
    bom_level: int | None = Field(default=None, description="层级。")
    is_top_level: bool | None = Field(default=None, description="是否顶层。")
    is_self_made: bool | None = Field(default=None, description="是否自制件。")
    sync_time: str | None = Field(default=None, description="同步时间，ISO 格式。")
    created_at: str | None = Field(default=None, description="入库时间，ISO 格式。")
    has_children: bool = Field(description="是否还有子节点。")
    children_loaded: bool = Field(description="前端是否已加载子节点。")
    children: list[BomTreeNodeResponse] = Field(default_factory=list, description="子节点。")


class BomTreeRootsResponse(BaseModel):
    """BOM 树根节点查询结果。"""

    machine_material_no: str | None = Field(default=None, description="原始查询入参。")
    machine_material_nos: list[str] = Field(default_factory=list, description="解析后的整机物料号列表。")
    total: int = Field(description="查询到的整机物料号总数。")
    root_count: int = Field(description="根节点数量。")
    root: BomTreeNodeResponse | None = Field(default=None, description="当仅有一个根节点时直接返回。")
    roots: list[BomTreeNodeResponse] = Field(default_factory=list, description="根节点列表。")


class BomTreeChildrenResponse(BaseModel):
    """BOM 树子节点查询结果。"""

    machine_material_no: str = Field(description="整机物料号。")
    parent_material_no: str = Field(description="父节点物料号。")
    total: int = Field(description="当前父节点下总子节点数。")
    count: int = Field(description="本次返回子节点数。")
    offset: int = Field(description="当前偏移量。")
    limit: int | None = Field(default=None, description="本次查询 limit。")
    has_more: bool = Field(description="是否还有更多子节点。")
    next_offset: int = Field(description="下一次查询偏移量。")
    items: list[BomTreeNodeResponse] = Field(default_factory=list, description="当前返回的子节点列表。")


class MachineCycleHistoryItemResponse(BaseModel):
    """整机周期历史记录。"""

    id: int = Field(description="记录 ID。")
    detail_id: str | None = Field(default=None, description="外部明细 ID。")
    machine_model: str | None = Field(default=None, description="机型。")
    product_series: str | None = Field(default=None, description="产品系列。")
    order_qty: float | None = Field(default=None, description="订单数量。")
    drawing_release_date: str | None = Field(default=None, description="发图日期，ISO 格式。")
    inspection_date: str | None = Field(default=None, description="完工/检验日期，ISO 格式。")
    customer_name: str | None = Field(default=None, description="客户名称。")
    contract_no: str | None = Field(default=None, description="合同号。")
    order_no: str | None = Field(default=None, description="订单号。")
    order_type: str | None = Field(default=None, description="订单类型。")
    cycle_days: float | None = Field(default=None, description="周期天数。")
    created_at: str | None = Field(default=None, description="入库时间，ISO 格式。")


class ProductionOrderHistoryItemResponse(BaseModel):
    """生产订单历史记录。"""

    id: int = Field(description="记录 ID。")
    production_order_no: str | None = Field(default=None, description="生产订单号。")
    material_no: str | None = Field(default=None, description="物料号。")
    material_desc: str | None = Field(default=None, description="物料描述。")
    machine_model: str | None = Field(default=None, description="机型。")
    plant: str | None = Field(default=None, description="工厂。")
    processing_dept: str | None = Field(default=None, description="加工部门。")
    start_time_actual: str | None = Field(default=None, description="实际投产时间，ISO 格式。")
    finish_time_actual: str | None = Field(default=None, description="实际完工时间，ISO 格式。")
    production_qty: float | None = Field(default=None, description="生产数量。")
    order_status: str | None = Field(default=None, description="订单状态。")
    sales_order_no: str | None = Field(default=None, description="关联销售订单号。")
    created_at: str | None = Field(default=None, description="入库时间，ISO 格式。")


BomTreeNodeResponse.model_rebuild()
