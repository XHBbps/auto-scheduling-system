from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.common.datetime_utils import utc_now
from app.common.exceptions import BizException, ErrorCode
from app.common.response import ApiResponse
from app.database import get_session
from app.repository.data_issue_repo import DataIssueRepo
from app.schemas.admin_schemas import IdStatusResponse
from app.schemas.issue_schemas import IssueActionRequest

router = APIRouter(prefix="/api/admin/issues", tags=["异常处理"])

require_issue_manage_permission = require_permission("issue.manage")


@router.post(
    "/{issue_id}/resolve",
    summary="解决异常",
    description="将指定异常记录标记为已解决，并写入处理备注与处理时间。",
    response_model=ApiResponse[IdStatusResponse],
)
async def resolve_issue(
    issue_id: int,
    req: IssueActionRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_issue_manage_permission),
):
    repo = DataIssueRepo(session)
    issue = await repo.get_by_id(issue_id)
    if not issue:
        raise BizException(ErrorCode.NOT_FOUND, f"异常记录不存在: {issue_id}")
    issue.status = "resolved"
    issue.remark = req.remark
    issue.handled_at = utc_now()
    await session.commit()
    return ApiResponse.ok(data={"id": issue.id, "status": issue.status})


@router.post(
    "/{issue_id}/ignore",
    summary="忽略异常",
    description="将指定异常记录标记为已忽略，并写入忽略备注与处理时间。",
    response_model=ApiResponse[IdStatusResponse],
)
async def ignore_issue(
    issue_id: int,
    req: IssueActionRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_issue_manage_permission),
):
    repo = DataIssueRepo(session)
    issue = await repo.get_by_id(issue_id)
    if not issue:
        raise BizException(ErrorCode.NOT_FOUND, f"异常记录不存在: {issue_id}")
    issue.status = "ignored"
    issue.remark = req.remark
    issue.handled_at = utc_now()
    await session.commit()
    return ApiResponse.ok(data={"id": issue.id, "status": issue.status})
