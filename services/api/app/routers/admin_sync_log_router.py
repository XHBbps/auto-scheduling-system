from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.common.exceptions import ErrorCode
from app.common.query_sort_utils import build_sort_expression, resolve_order_by
from app.common.response import ApiResponse
from app.database import get_session
from app.models.sync_job_log import SyncJobLog
from app.schemas.admin_schemas import SyncLogItemResponse
from app.schemas.common import PageResult
from app.services.sync_job_observability_service import serialize_sync_log

router = APIRouter(prefix="/api/admin/sync-logs", tags=["同步任务日志"])

require_sync_log_view_permission = require_permission("sync.log.view")


@router.get(
    "",
    summary="查询同步日志列表",
    description="按任务类型、来源系统、状态和分页条件查询同步任务执行日志，便于排查手动同步与定时同步问题。",
    response_model=ApiResponse[PageResult[SyncLogItemResponse]],
)
async def list_sync_logs(
    job_type: Optional[str] = None,
    source_system: Optional[str] = None,
    status: Optional[str] = None,
    page_no: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_sync_log_view_permission),
):
    stmt = select(SyncJobLog)
    count_conditions = []
    if job_type:
        count_conditions.append(SyncJobLog.job_type == job_type)
    if source_system:
        count_conditions.append(SyncJobLog.source_system == source_system)
    if status:
        count_conditions.append(SyncJobLog.status == status)
    if count_conditions:
        stmt = stmt.where(and_(*count_conditions))

    count_stmt = select(func.count()).select_from(SyncJobLog)
    if count_conditions:
        count_stmt = count_stmt.where(and_(*count_conditions))
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(
        *resolve_order_by(
            sort_expression=build_sort_expression(
                sort_field=sort_field,
                sort_order=sort_order,
                allowed_fields={
                    "id": SyncJobLog.id,
                    "job_type": SyncJobLog.job_type,
                    "source_system": SyncJobLog.source_system,
                    "status": SyncJobLog.status,
                    "success_count": SyncJobLog.success_count,
                    "fail_count": SyncJobLog.fail_count,
                    "start_time": SyncJobLog.start_time,
                    "end_time": SyncJobLog.end_time,
                    "message": SyncJobLog.message,
                    "created_at": SyncJobLog.created_at,
                },
            ),
            default_order_by=[desc(SyncJobLog.start_time)],
        )
    )
    stmt = stmt.offset((page_no - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    items = result.scalars().all()

    return ApiResponse.ok(data={
        "total": total,
        "page_no": page_no,
        "page_size": page_size,
        "items": [serialize_sync_log(i) for i in items],
    })


@router.get(
    "/{log_id}",
    summary="查看同步日志详情",
    description="查询单条同步任务日志详情，返回任务状态、执行统计、错误信息和时间字段。",
    response_model=ApiResponse[SyncLogItemResponse],
)
async def get_sync_log(
    log_id: int,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_sync_log_view_permission),
):
    entity = await session.get(SyncJobLog, log_id)
    if not entity:
        return ApiResponse.fail(code=ErrorCode.NOT_FOUND, message="记录不存在")
    return ApiResponse.ok(data=serialize_sync_log(entity))


@router.delete(
    "/{log_id}",
    summary="删除同步日志",
    description="删除指定同步日志记录，仅影响日志留痕，不会回滚已完成的数据同步结果。",
    response_model=ApiResponse[None],
)
async def delete_sync_log(
    log_id: int,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_permission("sync.manage")),
):
    entity = await session.get(SyncJobLog, log_id)
    if not entity:
        return ApiResponse.fail(code=ErrorCode.NOT_FOUND, message="记录不存在")
    await session.delete(entity)
    await session.commit()
    return ApiResponse.ok(data=None)
