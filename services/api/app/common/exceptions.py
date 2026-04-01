from enum import IntEnum


class ErrorCode(IntEnum):
    SUCCESS = 0
    PARAM_ERROR = 4001
    NOT_FOUND = 4002
    BIZ_VALIDATION_FAILED = 4003
    EXTERNAL_API_FAILED = 5001
    DB_ERROR = 5002
    SCHEDULE_CALC_FAILED = 5003
    EXPORT_FAILED = 5004


class BizException(Exception):
    def __init__(self, code: ErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(message)
