
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.baseline.assembly_time_default_service import AssemblyTimeDefaultService
from app.common.exceptions import ErrorCode
from app.common.response import ApiResponse
from app.database import get_session
from app.models.assembly_time import AssemblyTimeBaseline
from app.repository.assembly_time_repo import AssemblyTimeRepo, FINAL_ASSEMBLY_NAME
from app.schemas.admin_schemas import AssemblyTimeItemResponse, AssemblyTimeRequest, IdMachineModelResponse
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService

router = APIRouter(prefix="/api/admin/assembly-times", tags=["装配时长配置"])

require_settings_manage_permission = require_permission("settings.manage")


def _should_force_final_assembly_sequence(*, assembly_name: str, is_final_assembly: bool) -> bool:
    return is_final_assembly or (assembly_name or '').strip() == FINAL_ASSEMBLY_NAME


async def _resolve_production_sequence(repo: AssemblyTimeRepo, *, machine_model: str, assembly_name: str, is_final_assembly: bool, requested_sequence: int) -> tuple[int, bool]:
    force_final = _should_force_final_assembly_sequence(
        assembly_name=assembly_name,
        is_final_assembly=is_final_assembly,
    )
    if not force_final:
        return requested_sequence, is_final_assembly
    max_sub_sequence = await repo.find_max_sub_assembly_sequence(machine_model)
    next_sequence = int(max_sub_sequence or 0) + 1
    return next_sequence, True


@router.get(
    "",
    summary="查询装配时长配置",
    description="按整机机型、产品系列和部装名称查询装配时长基准；当前口径中部装记录用于零件排产倒排窗口，`is_final_assembly=true` 的记录表示整机总装时长。",
    response_model=ApiResponse[list[AssemblyTimeItemResponse]],
)
async def list_assembly_times(
    machine_model: Optional[str] = None,
    product_series: Optional[str] = None,
    assembly_name: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
):
    stmt = select(AssemblyTimeBaseline)
    conditions = []
    if machine_model:
        conditions.append(AssemblyTimeBaseline.machine_model == machine_model)
    if product_series:
        conditions.append(AssemblyTimeBaseline.product_series == product_series)
    if assembly_name:
        conditions.append(AssemblyTimeBaseline.assembly_name == assembly_name)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(AssemblyTimeBaseline.machine_model, AssemblyTimeBaseline.production_sequence)
    result = await session.execute(stmt)
    items = result.scalars().all()
    return ApiResponse.ok(data=[
        {
            "id": item.id,
            "machine_model": item.machine_model,
            "product_series": item.product_series,
            "assembly_name": item.assembly_name,
            "assembly_time_days": float(item.assembly_time_days),
            "is_final_assembly": item.is_final_assembly,
            "production_sequence": item.production_sequence,
            "is_default": item.is_default,
            "remark": item.remark,
        }
        for item in items
    ])


@router.post(
    "",
    summary="保存装配时长配置",
    description="新增或覆盖指定机型与部装的装配时长基准；当前口径中普通部装记录用于部装倒排窗口，整机总装记录会映射为 machine_assembly_days，并触发对应快照刷新。",
    response_model=ApiResponse[IdMachineModelResponse],
)
async def save_assembly_time(
    req: AssemblyTimeRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
):
    repo = AssemblyTimeRepo(session)
    default_service = AssemblyTimeDefaultService(session)
    production_sequence, is_final_assembly = await _resolve_production_sequence(
        repo,
        machine_model=req.machine_model,
        assembly_name=req.assembly_name,
        is_final_assembly=req.is_final_assembly,
        requested_sequence=req.production_sequence,
    )
    existing = await repo.find_by_model_and_assembly(req.machine_model, req.assembly_name)
    if existing:
        existing.product_series = req.product_series
        existing.assembly_time_days = req.assembly_time_days
        existing.is_final_assembly = is_final_assembly
        existing.production_sequence = production_sequence
        existing.is_default = req.is_default
        existing.remark = req.remark
        await session.flush()
        entity = existing
    else:
        entity = AssemblyTimeBaseline(
            machine_model=req.machine_model,
            product_series=req.product_series,
            assembly_name=req.assembly_name,
            assembly_time_days=req.assembly_time_days,
            is_final_assembly=is_final_assembly,
            production_sequence=production_sequence,
            is_default=req.is_default,
            remark=req.remark,
        )
        await repo.add(entity)

    await default_service.reconcile_final_assembly_sequence(req.machine_model)
    await ScheduleSnapshotRefreshService(session).refresh_by_product_model(
        req.machine_model,
        source="admin_assembly_time",
        reason="assembly_time_changed",
    )
    await session.commit()
    return ApiResponse.ok(data={"id": entity.id, "machine_model": entity.machine_model})


@router.delete(
    "/{record_id}",
    summary="删除装配时长配置",
    description="删除指定装配时长基准，并按机型刷新受影响的排产快照；若删除的是整机总装记录，将影响零件排产阶段的总装预留窗口。",
    response_model=ApiResponse[None],
)
async def delete_assembly_time(
    record_id: int,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
):
    default_service = AssemblyTimeDefaultService(session)
    entity = await session.get(AssemblyTimeBaseline, record_id)
    if not entity:
        return ApiResponse.fail(code=ErrorCode.NOT_FOUND, message="\u8bb0\u5f55\u4e0d\u5b58\u5728")
    machine_model = entity.machine_model
    await session.delete(entity)
    await session.flush()
    await default_service.reconcile_final_assembly_sequence(machine_model)
    await ScheduleSnapshotRefreshService(session).refresh_by_product_model(
        machine_model,
        source="admin_assembly_time",
        reason="assembly_time_deleted",
    )
    await session.commit()
    return ApiResponse.ok(data=None)
