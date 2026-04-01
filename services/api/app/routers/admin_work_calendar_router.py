
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.common.response import ApiResponse
from app.config import settings
from app.database import get_session
from app.repository.work_calendar_repo import WorkCalendarRepo
from app.schemas.admin_schemas import WorkCalendarBatchRequest, WorkCalendarRecordResponse, WorkCalendarUpdateResponse
from app.schemas.schedule_schemas import (
    ScheduleCalendarDayDetailResponse,
    ScheduleCalendarDaySummary,
    ScheduleCalendarOrderItem,
)
from app.services.schedule_query_service import ScheduleQueryService
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService

router = APIRouter(prefix="/api/admin/work-calendar", tags=["工作日历管理"])

require_settings_manage_permission = require_permission("settings.manage")


@router.get(
    "",
    summary="查询工作日历",
    description="查询指定月份或全部工作日历配置，用于维护节假日、调休日和排产工作日设置。",
    response_model=ApiResponse[list[WorkCalendarRecordResponse]],
)
async def get_work_calendar(
    month: Optional[str] = Query(None, description="要查询的月份；不传时返回全部工作日历配置，格式 yyyy-MM。"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
):
    repo = WorkCalendarRepo(session)
    if month:
        parts = month.split("-")
        year, m = int(parts[0]), int(parts[1])
        items = await repo.get_by_month(year, m)
    else:
        items = await repo.list_all()
    return ApiResponse.ok(data=[
        {
            "id": item.id,
            "calendar_date": item.calendar_date.isoformat(),
            "is_workday": item.is_workday,
            "remark": item.remark,
        }
        for item in items
    ])


@router.get(
    "/distribution",
    summary="查询排产日历分布",
    description="返回按天统计的交期、触发日和计划开工数量分布。",
    response_model=ApiResponse[list[ScheduleCalendarDaySummary]],
)
async def get_work_calendar_distribution(
    month: str = Query(..., description="要查询排产日历分布的月份，格式 yyyy-MM。"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
):
    parts = month.split("-")
    year, m = int(parts[0]), int(parts[1])
    service = ScheduleQueryService(session)
    items = await service.get_schedule_calendar_distribution(year, m)
    payload = [
        ScheduleCalendarDaySummary.model_validate(item).model_dump()
        for item in items
    ]
    return ApiResponse.ok(data=payload)


@router.get(
    "/day-detail",
    summary="查询排产日历单日明细",
    description="返回指定日期下的交付订单、触发订单和计划开工订单明细。",
    response_model=ApiResponse[ScheduleCalendarDayDetailResponse],
)
async def get_work_calendar_day_detail(
    date: str = Query(..., description="要查看排产日历明细的日期，格式 yyyy-MM-dd。"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
):
    target_date = datetime.strptime(date, "%Y-%m-%d").date()
    service = ScheduleQueryService(session)
    detail = await service.get_schedule_calendar_day_detail(target_date)
    payload = ScheduleCalendarDayDetailResponse(
        summary=ScheduleCalendarDaySummary.model_validate(detail["summary"]),
        delivery_orders=[
            ScheduleCalendarOrderItem.model_validate(item).model_dump()
            for item in detail["delivery_orders"]
        ],
        trigger_orders=[
            ScheduleCalendarOrderItem.model_validate(item).model_dump()
            for item in detail["trigger_orders"]
        ],
        planned_start_orders=[
            ScheduleCalendarOrderItem.model_validate(item).model_dump()
            for item in detail["planned_start_orders"]
        ],
    ).model_dump()
    return ApiResponse.ok(data=payload)


@router.post(
    "",
    summary="批量更新工作日历",
    description="批量新增或覆盖工作日历配置，并在提交后触发未来窗口快照刷新。",
    response_model=ApiResponse[WorkCalendarUpdateResponse],
)
async def update_work_calendar(
    req: WorkCalendarBatchRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
):
    repo = WorkCalendarRepo(session)
    count = 0
    for item in req.items:
        await repo.upsert(item.calendar_date, item.is_workday, item.remark)
        count += 1

    snapshot_refresh = await ScheduleSnapshotRefreshService(session).refresh_future_window(
        settings.snapshot_refresh_window_days,
        source="admin_work_calendar",
        reason="work_calendar_changed",
    )
    await session.commit()
    return ApiResponse.ok(data={"updated_count": count, "snapshot_refresh": snapshot_refresh})
