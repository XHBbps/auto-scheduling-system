
from app.common.enums import IssueStatus, OrderType, ScheduleStatus, WarningLevel


def test_schedule_status_values():
    assert ScheduleStatus.PENDING_DELIVERY == "pending_delivery"
    assert ScheduleStatus.PENDING_DRAWING == "pending_drawing"
    assert ScheduleStatus.MISSING_BOM == "missing_bom"
    assert ScheduleStatus.PENDING_TRIGGER == "pending_trigger"
    assert ScheduleStatus.SCHEDULABLE == "schedulable"
    assert ScheduleStatus.SCHEDULED == "scheduled"
    assert ScheduleStatus.SCHEDULED_STALE == "scheduled_stale"


def test_warning_level_values():
    assert WarningLevel.NORMAL == "normal"
    assert WarningLevel.ABNORMAL == "abnormal"


def test_order_type_values():
    assert OrderType.REGULAR.value == "1"
    assert OrderType.OPTIONAL.value == "2"
    assert OrderType.CUSTOM.value == "3"


def test_issue_status_values():
    assert IssueStatus.OPEN == "open"
    assert IssueStatus.RESOLVED == "resolved"
    assert IssueStatus.IGNORED == "ignored"
