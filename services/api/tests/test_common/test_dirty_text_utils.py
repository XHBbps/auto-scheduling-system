from app.common.dirty_text_utils import cleanup_issue_detail, normalize_legacy_issue_detail, repair_mojibake_text


def _to_mojibake(value: str) -> str:
    return value.encode("utf-8").decode("gb18030")


def test_repair_mojibake_text_repairs_project_domain_text():
    assert repair_mojibake_text(_to_mojibake("整机总装")) == "整机总装"
    assert repair_mojibake_text(_to_mojibake("机身")) == "机身"
    assert repair_mojibake_text(_to_mojibake("外购")) == "外购"


def test_repair_mojibake_text_keeps_clean_text():
    assert repair_mojibake_text("整机总装") == "整机总装"
    assert repair_mojibake_text("机身") == "机身"
    assert repair_mojibake_text("ABC-123") == "ABC-123"


def test_normalize_legacy_issue_detail_repairs_question_delimiters():
    value = "订单校验?order_no=SO001?涉及部装?机身?滑块?已按默认周期?"
    assert normalize_legacy_issue_detail(value) == "订单校验；order_no=SO001；涉及部装：机身、滑块；已按默认周期。"


def test_cleanup_issue_detail_repairs_both_mojibake_and_legacy_delimiters():
    value = f"{_to_mojibake('整机周期缺失')}?product_model=MC1-80?已按默认周期?"
    assert cleanup_issue_detail(value) == "整机周期缺失；product_model=MC1-80；已按默认周期。"
