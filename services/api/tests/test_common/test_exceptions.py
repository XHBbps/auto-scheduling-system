from app.common.exceptions import BizException, ErrorCode


def test_error_codes():
    assert ErrorCode.PARAM_ERROR == 4001
    assert ErrorCode.NOT_FOUND == 4002
    assert ErrorCode.BIZ_VALIDATION_FAILED == 4003
    assert ErrorCode.EXTERNAL_API_FAILED == 5001
    assert ErrorCode.DB_ERROR == 5002
    assert ErrorCode.SCHEDULE_CALC_FAILED == 5003
    assert ErrorCode.EXPORT_FAILED == 5004


def test_biz_exception():
    ex = BizException(ErrorCode.NOT_FOUND, "记录不存在")
    assert ex.code == 4002
    assert ex.message == "记录不存在"
