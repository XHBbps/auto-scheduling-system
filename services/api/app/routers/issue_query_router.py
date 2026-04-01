from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import require_permission
from app.common.response import ApiResponse
from app.database import get_session
from app.models.data_issue import DataIssueRecord
from app.schemas.common import PageResult
from app.repository.data_issue_repo import DataIssueRepo
from app.schemas.schedule_schemas import IssueItem

router = APIRouter(prefix="/api", tags=["异常查询"])

require_issue_view_permission = require_permission("issue.view")


@router.get(
    "/issues/options/issue-types",
    summary="获取异常类型筛选项",
    description="返回当前异常记录中已出现的异常类型列表，供异常列表页的筛选器下拉选择使用。",
    response_model=ApiResponse[list[str]],
)
async def get_issue_type_options(
    session: AsyncSession = Depends(get_session),
    _: object = Depends(require_issue_view_permission),
):
    stmt = select(distinct(DataIssueRecord.issue_type)).where(
        DataIssueRecord.issue_type.isnot(None)
    ).order_by(DataIssueRecord.issue_type)
    result = await session.execute(stmt)
    items = [row for row in result.scalars().all()]
    return ApiResponse.ok(data=items)


@router.get(
    "/issues",
    summary="查询异常列表",
    description="按异常类型、状态、业务主键和来源系统等条件分页查询异常记录，返回异常内容与关联快照字段。",
    response_model=ApiResponse[PageResult[IssueItem]],
)
async def list_issues(
    page_no: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    issue_type: Optional[str] = None,
    status: Optional[str] = None,
    biz_key: Optional[str] = None,
    source_system: Optional[str] = None,
    sort_field: Optional[str] = None,
    sort_order: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(require_issue_view_permission),
):
    repo = DataIssueRepo(session)
    rows, total = await repo.paginate_with_snapshot(
        page_no=page_no, page_size=page_size,
        issue_type=issue_type, status=status,
        biz_key=biz_key, source_system=source_system,
        sort_field=sort_field, sort_order=sort_order,
    )

    payload_items = []
    for item, snapshot in rows:
        payload = IssueItem.model_validate(item).model_dump()
        payload["material_no"] = snapshot.material_no if snapshot else None
        payload["custom_no"] = snapshot.custom_no if snapshot else None
        payload["order_no"] = snapshot.order_no if snapshot else None
        payload["contract_no"] = snapshot.contract_no if snapshot else None
        payload_items.append(payload)

    return ApiResponse.ok(data={
        "total": total,
        "page_no": page_no,
        "page_size": page_size,
        "items": payload_items,
    })
