import re

_MOJIBAKE_BAD_MARKERS = (
    "鏁存満",
    "鏈鸿韩",
    "闆朵欢",
    "鎬昏",
    "閮ㄨ",
    "鑷骇",
    "澶栬喘",
    "鍛ㄦ湡",
    "缂哄け",
    "鍙戝浘",
    "鐢垫皵",
    "浼犲姩",
    "绌烘皵",
    "鏈烘",
    "鐗╂枡",
)
_MOJIBAKE_GOOD_MARKERS = (
    "整机",
    "机身",
    "零件",
    "总装",
    "部装",
    "自产",
    "外购",
    "周期",
    "缺失",
    "发图",
    "电气",
    "传动",
    "空气",
    "物料",
    "按钮站",
    "编码器",
)


def repair_mojibake_text(value: str | None) -> str | None:
    if not value:
        return value

    try:
        repaired = value.encode("gb18030").decode("utf-8")
    except UnicodeError:
        return value

    if repaired == value:
        return value

    source_bad_score = _marker_score(value, _MOJIBAKE_BAD_MARKERS)
    repaired_good_score = _marker_score(repaired, _MOJIBAKE_GOOD_MARKERS)
    source_good_score = _marker_score(value, _MOJIBAKE_GOOD_MARKERS)

    if source_bad_score > 0 and repaired_good_score >= source_good_score:
        return repaired

    if repaired_good_score > source_good_score and repaired_good_score > 0:
        return repaired

    return value


def normalize_legacy_issue_detail(value: str | None) -> str | None:
    if not value or "?" not in value:
        return value

    normalized = value
    replacements = {
        "?order_no=": "；order_no=",
        "?product_model=": "；product_model=",
        "?material_no=": "；material_no=",
        "?涉及部装?": "；涉及部装：",
        "?涉及物料?": "；涉及物料：",
        "?已按默认": "；已按默认",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)

    normalized = re.sub(r"(涉及(?:部装|物料)：[^；。]+)", lambda m: m.group(1).replace("?", "、"), normalized)
    if normalized.endswith("?"):
        normalized = f"{normalized[:-1]}。"
    return normalized


def cleanup_issue_detail(value: str | None) -> str | None:
    normalized = normalize_legacy_issue_detail(value)
    if not normalized:
        return normalized

    parts = re.split(r"(；|。|、)", normalized)
    return "".join(part if part in {"；", "。", "、"} else (repair_mojibake_text(part) or part) for part in parts)


def _marker_score(text: str, markers: tuple[str, ...]) -> int:
    return sum(text.count(marker) for marker in markers)
