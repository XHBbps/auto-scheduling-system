from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    page_no: int = Field(default=1, ge=1, description="页码，从 1 开始。")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数，最大 100。")


class PageResult(BaseModel, Generic[T]):
    total: int = Field(description="总记录数。")
    page_no: int = Field(description="当前页码。")
    page_size: int = Field(description="当前页大小。")
    items: list[T] = Field(description="当前页数据列表。")
