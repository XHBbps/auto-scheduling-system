from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.common.exceptions import ErrorCode

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(default=0, description="业务状态码；0 表示成功。")
    message: str = Field(default="success", description="业务提示信息。")
    data: T | None = Field(default=None, description="实际返回数据。")

    @classmethod
    def ok(cls, data: Any = None) -> "ApiResponse[Any]":
        return cls(code=ErrorCode.SUCCESS, message="success", data=data)

    @classmethod
    def fail(cls, code: ErrorCode, message: str) -> "ApiResponse[Any]":
        return cls(code=code, message=message, data=None)
