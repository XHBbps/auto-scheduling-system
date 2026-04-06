"""Field name constants for Feishu bitable tables."""

# 生产订单表字段
PRODUCTION_ORDER_FIELDS = [
    "生产订单号",
    "物料号",
    "物料描述",
    "机床型号",
    "生产工厂",
    "加工部门",
    "投产时间",
    "完工时间",
    "订货数量",
    "生产订单状态",
    "销售订单号",
    "创建时间",
    "最后更新时间",
]

# 研究所表字段
RESEARCH_FIELDS = [
    "订单编号",
    "明细ID",
    "明细-物料编号",
    "发图时间（研究所）",
    "明细-产品型号",
    "产品大系列",
    "明细-数量",
    "报检时间",
    "定制编号",
    "客户名称",
    "合同编号",
    "事业群",
    "订单类型",
    "最后更新时间",
]


def extract_feishu_text(fields: dict, field_name: str) -> str | None:
    """Extract text value from Feishu multi-line text field structure."""
    val = fields.get(field_name)
    if val is None:
        return None
    if isinstance(val, list) and len(val) > 0:
        return val[0].get("text", "")
    if isinstance(val, str):
        return val
    return str(val)


def extract_feishu_number(fields: dict, field_name: str) -> float | None:
    """Extract numeric value from Feishu field."""
    val = fields.get(field_name)
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    return None


def extract_feishu_timestamp_ms(fields: dict, field_name: str) -> int | None:
    """Extract millisecond timestamp from Feishu date field."""
    val = fields.get(field_name)
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    return None
