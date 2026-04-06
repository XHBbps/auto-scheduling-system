from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, distinct, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import require_permission
from app.common.exceptions import BizException, ErrorCode
from app.common.response import ApiResponse
from app.database import get_session
from app.models.part_schedule_result import PartScheduleResult
from app.schemas.common import PageResult
from app.schemas.schedule_schemas import (
    DashboardOverviewResponse,
    IssueItem,
    PartScheduleItem,
    PartScheduleListItem,
    ScheduleDetailResponse,
    ScheduleListItem,
)
from app.services.schedule_query_service import ScheduleQueryService

router = APIRouter(prefix="/api", tags=["排产查询"])

require_schedule_view_permission = require_permission("schedule.view")


@router.get(
    "/schedules/options/product-series",
    summary="获取产品系列筛选项",
    description="返回当前排产数据中可用的产品系列列表，供整机排产列表页的筛选条件下拉选择使用。",
    response_model=ApiResponse[list[str]],
)
async def get_product_series_options(
    session: AsyncSession = Depends(get_session),
    _: object = Depends(require_schedule_view_permission),
) -> ApiResponse[Any]:
    service = ScheduleQueryService(session)
    items = await service.list_product_series_options()
    return ApiResponse.ok(data=items)


@router.get(
    "/dashboard/overview",
    summary="获取排产总览",
    description="返回整机排产、零件排产、时间窗口统计和交付风险订单等总览信息，供 Dashboard 页面展示。",
    response_model=ApiResponse[DashboardOverviewResponse],
)
async def get_dashboard_overview(
    session: AsyncSession = Depends(get_session),
    _: object = Depends(require_schedule_view_permission),
) -> ApiResponse[Any]:
    service = ScheduleQueryService(session)
    result = await service.get_dashboard_overview()
    payload = DashboardOverviewResponse(
        machine_summary={
            **result["machine_summary"],
            "warning_orders": [
                ScheduleListItem.model_validate(item).model_dump()
                for item in result["machine_summary"]["warning_orders"]
            ],
        },
        part_summary=result["part_summary"],
        today_summary=result["today_summary"],
        week_summary=result["week_summary"],
        month_summary=result["month_summary"],
        delivery_trends=result["delivery_trends"],
        business_group_summary=result["business_group_summary"],
        abnormal_machine_orders=[
            ScheduleListItem.model_validate(item).model_dump() for item in result["abnormal_machine_orders"]
        ],
        delivery_risk_orders=[
            ScheduleListItem.model_validate(item).model_dump() for item in result["delivery_risk_orders"]
        ],
    ).model_dump()
    return ApiResponse.ok(data=payload)


@router.get(
    "/schedules",
    summary="查询整机排产列表",
    description="按合同号、客户、机型、排产状态、预警等级和日期范围等条件分页查询整机排产列表。",
    response_model=ApiResponse[PageResult[ScheduleListItem]],
)
async def list_schedules(
    page_no: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    contract_no: str | None = None,
    customer_name: str | None = None,
    product_series: str | None = None,
    product_model: str | None = None,
    plant: str | None = None,
    order_no: str | None = None,
    schedule_status: str | None = None,
    schedule_bucket: str | None = Query(None, pattern="^(unscheduled|risk)$"),
    warning_level: str | None = None,
    drawing_released: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_field: str | None = None,
    sort_order: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(require_schedule_view_permission),
) -> ApiResponse[Any]:
    service = ScheduleQueryService(session)
    result = await service.list_schedules(
        page_no=page_no,
        page_size=page_size,
        contract_no=contract_no,
        customer_name=customer_name,
        product_series=product_series,
        product_model=product_model,
        plant=plant,
        order_no=order_no,
        schedule_status=schedule_status,
        schedule_bucket=schedule_bucket,
        warning_level=warning_level,
        drawing_released=drawing_released,
        date_from=date_from,
        date_to=date_to,
        sort_field=sort_field,
        sort_order=sort_order,
    )
    result["items"] = [ScheduleListItem.model_validate(item).model_dump() for item in result["items"]]
    return ApiResponse.ok(data=result)


@router.get(
    "/part-schedules",
    summary="查询零件排产列表",
    description="按订单、部装、零件、关键件和日期范围等条件分页查询零件排产结果。",
    response_model=ApiResponse[PageResult[PartScheduleListItem]],
)
async def list_part_schedules(
    page_no: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    order_line_id: int | None = None,
    contract_no: str | None = None,
    order_no: str | None = None,
    plant: str | None = None,
    assembly_name: str | None = None,
    part_material_no: str | None = None,
    key_part_name: str | None = None,
    key_part_material_no: str | None = None,
    warning_level: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_field: str | None = None,
    sort_order: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(require_schedule_view_permission),
) -> ApiResponse[Any]:
    service = ScheduleQueryService(session)
    result = await service.list_part_schedules(
        page_no=page_no,
        page_size=page_size,
        order_line_id=order_line_id,
        contract_no=contract_no,
        order_no=order_no,
        plant=plant,
        assembly_name=assembly_name,
        part_material_no=part_material_no,
        key_part_name=key_part_name,
        key_part_material_no=key_part_material_no,
        warning_level=warning_level,
        date_from=date_from,
        date_to=date_to,
        sort_field=sort_field,
        sort_order=sort_order,
    )
    result["items"] = [PartScheduleListItem.model_validate(item).model_dump() for item in result["items"]]
    return ApiResponse.ok(data=result)


@router.get(
    "/part-schedules/options/assembly-names",
    summary="获取部装筛选项",
    description="返回当前零件排产结果中可用的部装名称列表，供零件排产列表页的筛选器使用。",
    response_model=ApiResponse[list[str]],
)
async def get_part_schedule_assembly_name_options(
    session: AsyncSession = Depends(get_session),
    _: object = Depends(require_schedule_view_permission),
) -> ApiResponse[Any]:
    stmt = (
        select(distinct(PartScheduleResult.assembly_name))
        .where(
            and_(
                PartScheduleResult.assembly_name.isnot(None),
                or_(
                    PartScheduleResult.part_material_no.isnot(None),
                    PartScheduleResult.part_name.isnot(None),
                    PartScheduleResult.key_part_material_no.isnot(None),
                    PartScheduleResult.key_part_name.isnot(None),
                ),
            )
        )
        .order_by(PartScheduleResult.assembly_name)
    )
    result = await session.execute(stmt)
    items = [row for row in result.scalars().all() if row]
    return ApiResponse.ok(data=items)


@router.get(
    "/schedules/{order_line_id}",
    summary="获取排产详情",
    description="返回单个订单行的整机排产、零件排产和异常记录。",
    response_model=ApiResponse[ScheduleDetailResponse],
)
async def get_schedule_detail(
    order_line_id: int,
    session: AsyncSession = Depends(get_session),
    _: object = Depends(require_schedule_view_permission),
) -> ApiResponse[Any]:
    service = ScheduleQueryService(session)
    detail = await service.get_detail(order_line_id)
    if not detail:
        raise BizException(ErrorCode.NOT_FOUND, f"未找到对应的排产订单: {order_line_id}")
    return ApiResponse.ok(
        data={
            "machine_schedule": ScheduleListItem.model_validate(detail["machine_schedule"]).model_dump(),
            "part_schedules": [PartScheduleItem.model_validate(item).model_dump() for item in detail["part_schedules"]],
            "issues": [IssueItem.model_validate(item).model_dump() for item in detail["issues"]],
        }
    )
