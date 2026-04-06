from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.common.datetime_utils import utc_now
from app.common.exceptions import ErrorCode
from app.common.part_cycle_precision import normalize_part_cycle_days, normalize_part_unit_cycle_days
from app.common.response import ApiResponse
from app.common.text_parse_utils import extract_part_type
from app.database import get_session
from app.models.part_cycle_baseline import PartCycleBaseline
from app.repository.part_cycle_baseline_repo import PartCycleBaselineRepo
from app.schemas.admin_schemas import (
    IdPartTypeResponse,
    PartCycleBaselineItemResponse,
    PartCycleBaselineRequest,
    SyncTriggerResponse,
)
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService
from app.sync.manual_sync_job_service import ManualSyncTaskService

router = APIRouter(prefix="/api/admin/part-cycle-baselines", tags=["零件周期基准"])

require_settings_manage_permission = require_permission("settings.manage")


def _resolve_part_type(
    *,
    part_type: str | None = None,
    material_no: str | None = None,
    core_part_name: str | None = None,
    material_desc: str | None = None,
) -> str:
    for candidate in [part_type, core_part_name, extract_part_type(material_desc or ""), material_no]:
        value = (candidate or "").strip()
        if value:
            return value
    return (material_desc or "").strip()[:20]


def _normalize_plant(plant: str | None) -> str | None:
    value = (plant or "").strip()
    return value or None


def _serialize_part_cycle_baseline(item: PartCycleBaseline) -> dict:
    part_type = _resolve_part_type(
        material_no=item.material_no,
        core_part_name=item.core_part_name,
        material_desc=item.material_desc,
    )
    return {
        "id": item.id,
        "part_type": part_type,
        "material_no": item.material_no,
        "material_desc": item.material_desc,
        "core_part_name": item.core_part_name,
        "machine_model": item.machine_model,
        "plant": item.plant,
        "ref_batch_qty": float(item.ref_batch_qty),
        "cycle_days": float(normalize_part_cycle_days(item.cycle_days)),
        "unit_cycle_days": float(normalize_part_unit_cycle_days(item.unit_cycle_days)),
        "sample_count": int(item.sample_count or 0),
        "source_updated_at": item.source_updated_at.isoformat() if item.source_updated_at else None,
        "cycle_source": item.cycle_source,
        "match_rule": item.match_rule,
        "confidence_level": item.confidence_level,
        "is_default": item.is_default,
        "is_active": item.is_active,
        "remark": item.remark,
    }


@router.get(
    "",
    summary="查询零件周期基准",
    description="按零件类型、机型、工厂和启用状态查询零件周期基准；当前口径中该基准表示单个零件自身周期，部装组倒排时会额外取关键件周期作为锚点。",
    response_model=ApiResponse[list[PartCycleBaselineItemResponse]],
)
async def list_part_cycle_baselines(
    part_type: str | None = None,
    material_no: str | None = None,
    core_part_name: str | None = None,
    machine_model: str | None = None,
    plant: str | None = None,
    is_active: bool | None = None,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
) -> ApiResponse[Any]:
    stmt = select(PartCycleBaseline)
    conditions = []
    search_part_type = (part_type or material_no or "").strip()
    if search_part_type:
        conditions.append(
            or_(
                PartCycleBaseline.material_no.ilike(f"%{search_part_type}%"),
                PartCycleBaseline.core_part_name.ilike(f"%{search_part_type}%"),
                PartCycleBaseline.material_desc.ilike(f"%{search_part_type}%"),
            )
        )
    if core_part_name:
        conditions.append(PartCycleBaseline.core_part_name.ilike(f"%{core_part_name}%"))
    if machine_model:
        conditions.append(PartCycleBaseline.machine_model.ilike(f"%{machine_model}%"))
    if plant:
        conditions.append(PartCycleBaseline.plant.ilike(f"%{plant}%"))
    if is_active is not None:
        conditions.append(PartCycleBaseline.is_active == is_active)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(
        PartCycleBaseline.machine_model.asc(),
        PartCycleBaseline.plant.asc().nullsfirst(),
        PartCycleBaseline.core_part_name.asc(),
        PartCycleBaseline.id.asc(),
    )
    result = await session.execute(stmt)
    items = result.scalars().all()
    return ApiResponse.ok(data=[_serialize_part_cycle_baseline(item) for item in items])


@router.post(
    "",
    summary="保存零件周期基准",
    description="新增或覆盖零件周期基准；当前口径中保存的是零件自身周期，关键件倒排周期由排产阶段基于关键件识别结果选取，并按零件类型、机型、工厂批量刷新受影响的排产快照。",
    response_model=ApiResponse[IdPartTypeResponse],
)
async def save_part_cycle_baseline(
    req: PartCycleBaselineRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
) -> ApiResponse[Any]:
    machine_model = (req.machine_model or "").strip()
    if not machine_model:
        return ApiResponse.fail(code=ErrorCode.BIZ_VALIDATION_FAILED, message="机床型号不能为空")

    material_desc = req.material_desc
    part_type = _resolve_part_type(
        part_type=req.part_type,
        material_no=req.material_no,
        core_part_name=req.core_part_name,
        material_desc=material_desc,
    )
    if not part_type:
        return ApiResponse.fail(code=ErrorCode.BIZ_VALIDATION_FAILED, message="零件类型不能为空")

    plant = _normalize_plant(req.plant)
    repo = PartCycleBaselineRepo(session)
    payload = {
        "material_no": part_type,
        "material_desc": material_desc,
        "core_part_name": part_type,
        "machine_model": machine_model,
        "plant": plant,
        "ref_batch_qty": Decimal(str(req.ref_batch_qty)),
        "cycle_days": normalize_part_cycle_days(req.cycle_days),
        "unit_cycle_days": normalize_part_unit_cycle_days(req.unit_cycle_days),
        "sample_count": 0,
        "source_updated_at": utc_now(),
        "cycle_source": "manual",
        "match_rule": req.match_rule or ("part_type_exact_with_plant" if plant else "part_type_exact"),
        "confidence_level": req.confidence_level or "manual",
        "is_default": req.is_default,
        "is_active": req.is_active,
        "remark": req.remark,
    }

    try:
        entity = await repo.save_manual(record_id=req.id, data=payload)
        await ScheduleSnapshotRefreshService(session).refresh_by_part_type(
            part_type,
            machine_model=machine_model,
            plant=plant,
            source="admin_part_cycle",
            reason="part_cycle_baseline_changed",
        )
        await session.commit()
        return ApiResponse.ok(data={"id": entity.id, "part_type": part_type, "material_no": entity.material_no})
    except IntegrityError:
        await session.rollback()
        return ApiResponse.fail(
            code=ErrorCode.BIZ_VALIDATION_FAILED, message="相同零件类型 / 机型 / 工厂的基准记录已存在"
        )


@router.post(
    "/rebuild",
    summary="触发零件周期基准重建",
    description="将零件周期基准重建任务加入后台队列；当前重建结果对应零件自身周期，若已有同类任务在运行或排队，则不会重复创建。",
    response_model=ApiResponse[SyncTriggerResponse],
)
async def rebuild_part_cycle_baselines(
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
) -> ApiResponse[Any]:
    job_id, status, created = await ManualSyncTaskService().enqueue_part_cycle_baseline_rebuild(
        session,
        operator_name="system",
        message="手动触发零件周期基准重建，任务已进入后台执行。",
    )
    message = "零件周期基准重建任务已入队。" if created else "已有零件周期基准重建任务在运行或排队，未重复创建。"
    return ApiResponse.ok(
        data={
            "job_id": job_id,
            "status": status,
            "message": message,
        }
    )


@router.delete(
    "/{record_id}",
    summary="删除零件周期基准",
    description="删除指定零件周期基准，并按零件类型、机型、工厂批量刷新对应排产快照；当前删除的是零件自身周期基准，不直接等同关键件倒排周期。",
    response_model=ApiResponse[None],
)
async def delete_part_cycle_baseline(
    record_id: int,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_settings_manage_permission),
) -> ApiResponse[Any]:
    entity = await session.get(PartCycleBaseline, record_id)
    if not entity:
        return ApiResponse.fail(code=ErrorCode.NOT_FOUND, message="记录不存在")
    part_type = _resolve_part_type(
        material_no=entity.material_no,
        core_part_name=entity.core_part_name,
        material_desc=entity.material_desc,
    )
    machine_model = entity.machine_model
    plant = entity.plant
    await session.delete(entity)
    await ScheduleSnapshotRefreshService(session).refresh_by_part_type(
        part_type,
        machine_model=machine_model,
        plant=plant,
        source="admin_part_cycle",
        reason="part_cycle_baseline_deleted",
    )
    await session.commit()
    return ApiResponse.ok(data=None)
