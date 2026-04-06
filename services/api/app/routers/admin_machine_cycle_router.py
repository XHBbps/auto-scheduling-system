from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.baseline.machine_cycle_baseline_service import MachineCycleBaselineService
from app.common.auth import CurrentUserIdentity, require_permission
from app.common.exceptions import ErrorCode
from app.common.query_sort_utils import build_sort_expression, resolve_order_by
from app.common.response import ApiResponse
from app.database import get_session
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.repository.machine_cycle_baseline_repo import MachineCycleBaselineRepo
from app.schemas.admin_schemas import (
    IdMachineModelResponse,
    MachineCycleBaselineItemResponse,
    MachineCycleBaselineRebuildResponse,
    MachineCycleBaselineRequest,
)
from app.schemas.common import PageResult
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService

router = APIRouter(prefix="/api/admin/machine-cycle-baselines", tags=["整机周期基准"])

require_settings_manage_permission = require_permission("settings.manage")


@router.get(
    "",
    summary="查询整机周期基准",
    description="分页查询整机主周期基准，支持按机型、产品系列和启用状态筛选；当前口径用于倒排 trigger_date / planned_start_date，不包含单独预留的整机总装时长。",
    response_model=ApiResponse[PageResult[MachineCycleBaselineItemResponse]],
)
async def list_machine_cycle_baselines(
    machine_model: str | None = None,
    product_series: str | None = None,
    is_active: bool | None = None,
    page_no: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: str | None = None,
    sort_order: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
) -> ApiResponse[Any]:
    conditions = []
    if machine_model:
        conditions.append(MachineCycleBaseline.machine_model.ilike(f"%{machine_model}%"))
    if product_series:
        conditions.append(MachineCycleBaseline.product_series.ilike(f"%{product_series}%"))
    if is_active is not None:
        conditions.append(MachineCycleBaseline.is_active == is_active)
    where = and_(*conditions) if conditions else True

    count_stmt = select(func.count()).select_from(MachineCycleBaseline).where(where)
    total = (await session.execute(count_stmt)).scalar_one()
    stmt = (
        select(MachineCycleBaseline)
        .where(where)
        .order_by(
            *resolve_order_by(
                sort_expression=build_sort_expression(
                    sort_field=sort_field,
                    sort_order=sort_order,
                    allowed_fields={
                        "id": MachineCycleBaseline.id,
                        "machine_model": MachineCycleBaseline.machine_model,
                        "product_series": MachineCycleBaseline.product_series,
                        "order_qty": MachineCycleBaseline.order_qty,
                        "cycle_days_median": MachineCycleBaseline.cycle_days_median,
                        "sample_count": MachineCycleBaseline.sample_count,
                        "is_active": MachineCycleBaseline.is_active,
                        "remark": MachineCycleBaseline.remark,
                    },
                ),
                default_order_by=[MachineCycleBaseline.machine_model, MachineCycleBaseline.order_qty],
            )
        )
        .offset((page_no - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    items = result.scalars().all()
    return ApiResponse.ok(
        data={
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
            "items": [
                {
                    "id": item.id,
                    "product_series": item.product_series,
                    "machine_model": item.machine_model,
                    "order_qty": float(item.order_qty),
                    "cycle_days_median": float(item.cycle_days_median),
                    "sample_count": item.sample_count,
                    "is_active": item.is_active,
                    "remark": item.remark,
                }
                for item in items
            ],
        }
    )


@router.post(
    "",
    summary="保存整机周期基准",
    description="新增或覆盖整机主周期基准记录；当前口径仅表示整机主周期，不含单独预留的整机总装时长，并在保存后刷新对应机型的排产快照。",
    response_model=ApiResponse[IdMachineModelResponse],
)
async def save_machine_cycle_baseline(
    req: MachineCycleBaselineRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
) -> ApiResponse[Any]:
    repo = MachineCycleBaselineRepo(session)
    entity = await repo.upsert_baseline(
        product_series=req.product_series or "",
        machine_model=req.machine_model,
        order_qty=Decimal(str(req.order_qty)),
        data={
            "cycle_days_median": Decimal(str(req.cycle_days_median)),
            "sample_count": req.sample_count,
            "is_active": req.is_active,
            "remark": req.remark,
        },
    )
    await ScheduleSnapshotRefreshService(session).refresh_by_product_model(
        entity.machine_model,
        source="admin_machine_cycle",
        reason="machine_cycle_baseline_changed",
    )
    await session.commit()
    return ApiResponse.ok(data={"id": entity.id, "machine_model": entity.machine_model})


@router.post(
    "/rebuild",
    summary="重建整机周期基准",
    description="基于历史数据重新计算整机主周期基准，并全量刷新未关闭订单的排产快照；当前重建结果仍只对应整机主周期，不含单独总装预留。",
    response_model=ApiResponse[MachineCycleBaselineRebuildResponse],
)
async def rebuild_machine_cycle_baselines(
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
) -> ApiResponse[Any]:
    result = await MachineCycleBaselineService(session).rebuild()
    await ScheduleSnapshotRefreshService(session).rebuild_all_open_snapshots(
        source="admin_machine_cycle",
        reason="machine_cycle_baseline_rebuilt",
    )
    await session.commit()
    return ApiResponse.ok(data=result)


@router.delete(
    "/{record_id}",
    summary="删除整机周期基准",
    description="删除指定整机主周期基准记录，并刷新对应机型的排产快照。",
    response_model=ApiResponse[None],
)
async def delete_machine_cycle_baseline(
    record_id: int,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
) -> ApiResponse[Any]:
    entity = await session.get(MachineCycleBaseline, record_id)
    if not entity:
        return ApiResponse.fail(code=ErrorCode.NOT_FOUND, message="\u8bb0\u5f55\u4e0d\u5b58\u5728")
    machine_model = entity.machine_model
    await session.delete(entity)
    await ScheduleSnapshotRefreshService(session).refresh_by_product_model(
        machine_model,
        source="admin_machine_cycle",
        reason="machine_cycle_baseline_deleted",
    )
    await session.commit()
    return ApiResponse.ok(data=None)
