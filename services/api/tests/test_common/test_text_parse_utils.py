from app.common.text_parse_utils import (
    extract_part_type,
    extract_chinese_prefix,
    is_excluded_assembly,
    normalize_assembly_name,
)


def test_extract_chinese_prefix_normal():
    assert extract_chinese_prefix("机身MC1-80.1(253464)") == "机身"


def test_extract_chinese_prefix_multi_char():
    assert extract_chinese_prefix("空气管路总成 ABC-123") == "空气管路总成"


def test_extract_chinese_prefix_only_chinese():
    assert extract_chinese_prefix("传动") == "传动"


def test_extract_chinese_prefix_no_chinese():
    assert extract_chinese_prefix("ABC-123") == ""


def test_extract_chinese_prefix_empty():
    assert extract_chinese_prefix("") == ""


def test_extract_part_type():
    assert extract_part_type("右导轨总成MC1-25.1-13") == "右导轨总成"


def test_is_excluded_assembly():
    assert is_excluded_assembly("润滑系统") is True
    assert is_excluded_assembly("附件") is True
    assert is_excluded_assembly("油漆") is True
    assert is_excluded_assembly("标牌") is True
    assert is_excluded_assembly("包装") is True
    assert is_excluded_assembly("机身") is False
    assert is_excluded_assembly("传动") is False


def test_normalize_assembly_name_core_categories():
    assert normalize_assembly_name("机身体总成MC2-200.1-1") == "机身"
    assert normalize_assembly_name("滑块部装MC1-80") == "滑块"
    assert normalize_assembly_name("电气箱总成MC1-80") == "电气"
    assert normalize_assembly_name("按钮站总成MC1-80") == "电气"
    assert normalize_assembly_name("飞轮MC2-200") == "传动"
    assert normalize_assembly_name("储气筒MC2-200") == "空气管路"


def test_normalize_assembly_name_filters_small_parts():
    assert normalize_assembly_name("平垫圈MC2-200") == ""
    assert normalize_assembly_name("电机轮端盖MC2-200") == ""
    assert normalize_assembly_name("润滑系统MC2-200") == ""
