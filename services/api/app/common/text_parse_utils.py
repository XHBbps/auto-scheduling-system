import re

_CHINESE_PREFIX_RE = re.compile(r"^[\u4e00-\u9fff]+")
_EXCLUDED_PREFIXES = {"润滑", "附件", "油漆", "标牌", "包装"}
_ASSEMBLY_ALIAS_RULES = [
    ("机身", "机身"),
    ("滑块", "滑块"),
    ("平衡缸", "平衡缸"),
    ("空气管路", "空气管路"),
    ("储气筒", "空气管路"),
    ("双联阀", "空气管路"),
    ("连接头", "空气管路"),
    ("电气", "电气"),
    ("按钮站", "电气"),
    ("编码器", "电气"),
    ("光电", "电气"),
    ("传动", "传动"),
    ("飞轮", "传动"),
    ("齿轮", "传动"),
    ("轴承座", "传动"),
    ("支承", "传动"),
]


def extract_chinese_prefix(text: str) -> str:
    """取字符串开头连续中文字符作为部装名。"""
    if not text:
        return ""
    m = _CHINESE_PREFIX_RE.match(text)
    return m.group(0) if m else ""


def extract_part_type(text: str) -> str:
    """提取零件类型，当前规则为物料描述开头的连续中文前缀。"""
    return extract_chinese_prefix(text)


def is_excluded_assembly(assembly_name: str) -> bool:
    """判断部装名是否属于排除项。"""
    return any(assembly_name.startswith(prefix) for prefix in _EXCLUDED_PREFIXES)


def normalize_assembly_name(text: str) -> str:
    """将 BOM 原始中文前缀归一为较稳定的部装分类名。"""
    prefix = extract_chinese_prefix(text)
    if not prefix or is_excluded_assembly(prefix):
        return ""

    for keyword, normalized in _ASSEMBLY_ALIAS_RULES:
        if keyword in prefix:
            return normalized

    if "总成" in prefix or "部装" in prefix:
        return prefix

    return ""
