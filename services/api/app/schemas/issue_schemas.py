from pydantic import BaseModel, ConfigDict, Field


class IssueListFilter(BaseModel):
    """异常列表筛选条件。"""

    page_no: int = Field(default=1, description="页码，从 1 开始。")
    page_size: int = Field(default=20, description="每页条数。")
    issue_type: str | None = Field(default=None, description="异常类型。")
    status: str | None = Field(default=None, description="异常状态，如 open / resolved / ignored。")
    biz_key: str | None = Field(default=None, description="业务主键，通常为订单行 ID。")
    source_system: str | None = Field(default=None, description="异常来源系统。")


class IssueActionRequest(BaseModel):
    """异常处理请求。"""

    model_config = ConfigDict(json_schema_extra={"example": {"remark": "人工确认已处理"}})

    remark: str | None = Field(default=None, description="处理备注。")
