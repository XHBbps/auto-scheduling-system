import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.common.datetime_utils import utc_now
from app.common.exceptions import BizException, ErrorCode
from app.common.response import ApiResponse
from app.database import get_session
from app.repository.order_schedule_snapshot_repo import OrderScheduleSnapshotRepo
from app.scheduler.schedule_orchestrator import ScheduleOrchestrator
from app.schemas.admin_schemas import (
    ScheduleRunRequest,
    ScheduleRunResponse,
    SingleOrderPartScheduleRunRequest,
    SingleOrderPartScheduleRunResponse,
    SnapshotObservabilityResponse,
    SnapshotRefreshResult,
)
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/schedule", tags=["排产管理"])

require_schedule_manage_permission = require_permission("schedule.manage")


class _SingleOrderScheduleAbort(Exception):
    def __init__(self, payload: dict):
        self.payload = payload
        super().__init__(payload.get("message", "single order schedule aborted"))


async def _find_schedulable_order_line_ids(session: AsyncSession) -> list[int]:
    snapshot_refresh_service = ScheduleSnapshotRefreshService(session)
    await snapshot_refresh_service.ensure_seeded(
        source="admin_schedule",
        reason="default_schedulable_lookup_seed",
    )
    snapshot_repo = OrderScheduleSnapshotRepo(session)
    return await snapshot_repo.list_schedulable_order_line_ids()


@router.post(
    "/run",
    summary="批量执行排产",
    description="对指定或系统自动筛选出的可排产订单执行整机与零件排产。",
    response_model=ApiResponse[ScheduleRunResponse],
)
async def run_schedule(
    req: ScheduleRunRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_schedule_manage_permission),
):
    try:
        order_line_ids = req.order_line_ids
        if not order_line_ids:
            order_line_ids = await _find_schedulable_order_line_ids(session)
            if not order_line_ids:
                return ApiResponse.ok(
                    data={
                        "run_batch_no": None,
                        "total": 0,
                        "success_count": 0,
                        "fail_count": 0,
                        "message": "当前没有可排产订单",
                    }
                )

        orchestrator = ScheduleOrchestrator(session)
        batch_result = await orchestrator.schedule_batch(order_line_ids)
        await session.commit()
        run_batch_no = f"SCH{utc_now().strftime('%Y%m%d%H%M%S')}"
        return ApiResponse.ok(
            data={
                "run_batch_no": run_batch_no,
                "total": batch_result["total"],
                "success_count": batch_result["scheduled"],
                "fail_count": batch_result["failed"],
            }
        )
    except BizException:
        raise
    except Exception as exc:
        logger.error("Schedule run failed: %s", exc, exc_info=True)
        raise BizException(ErrorCode.SCHEDULE_CALC_FAILED, "排产执行失败，请稍后重试或联系管理员") from exc


@router.post(
    "/run-one-part",
    summary="执行单订单零件排产",
    description="先执行前置校验，校验通过后只对单个订单行生成排产结果。",
    response_model=ApiResponse[SingleOrderPartScheduleRunResponse],
)
async def run_one_part_schedule(
    req: SingleOrderPartScheduleRunRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_schedule_manage_permission),
):
    orchestrator = ScheduleOrchestrator(session)
    validation = await orchestrator.validate_part_schedule_run(req.order_line_id)
    if not validation.get("precheck_passed"):
        await orchestrator.handle_part_schedule_precheck_failure(validation)
        validation.pop("check", None)
        await session.commit()
        return ApiResponse.ok(data=validation)

    try:
        async with session.begin_nested():
            result = await orchestrator.schedule_order(req.order_line_id)
            if not result.get("success"):
                raise _SingleOrderScheduleAbort(
                    {
                        "order_line_id": req.order_line_id,
                        "success": False,
                        "precheck_passed": True,
                        "status": result.get("status", "schedule_failed"),
                        "message": result.get("reason", "排产执行失败。"),
                        "validation_items": [],
                        "machine_schedule_built": False,
                        "part_schedule_built": False,
                    }
                )

            part_schedules = result.get("part_schedules") or []
            if not part_schedules:
                raise _SingleOrderScheduleAbort(
                    {
                        "order_line_id": req.order_line_id,
                        "success": False,
                        "precheck_passed": True,
                        "status": "part_schedule_empty",
                        "message": "排产未生成任何结果，请检查零件/BOM 数据。",
                        "validation_items": [
                            ScheduleOrchestrator._build_validation_item(
                                code="part_schedule_empty",
                                label="零件数据",
                                message="执行后未生成排产结果，请检查部装和零件数据。",
                            )
                        ],
                        "machine_schedule_built": False,
                        "part_schedule_built": False,
                    }
                )

            warning_items = orchestrator.collect_schedule_warning_items(
                result["machine_schedule"],
                part_schedules,
            )
            payload = {
                "order_line_id": req.order_line_id,
                "success": True,
                "precheck_passed": True,
                "status": "scheduled",
                "message": "排产已完成。",
                "validation_items": warning_items,
                "machine_schedule_built": result.get("machine_schedule") is not None,
                "part_schedule_built": bool(part_schedules),
                "warning_summary": "；".join(item["message"] for item in warning_items) if warning_items else None,
            }
        await session.commit()
        return ApiResponse.ok(data=payload)
    except _SingleOrderScheduleAbort as exc:
        await session.commit()
        return ApiResponse.ok(data=exc.payload)
    except BizException:
        raise
    except Exception as exc:
        logger.error("Single order part schedule run failed: %s", exc, exc_info=True)
        raise BizException(ErrorCode.SCHEDULE_CALC_FAILED, "单订单排产执行失败，请稍后重试或联系管理员") from exc


@router.post(
    "/snapshots/rebuild",
    summary="重建排产快照",
    description="按窗口天数或全量模式重建排产快照，适用于规则变更、补数完成后的状态回收。",
    response_model=ApiResponse[SnapshotRefreshResult],
)
async def rebuild_schedule_snapshots(
    window_days: int | None = Query(None, ge=1),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_schedule_manage_permission),
):
    service = ScheduleSnapshotRefreshService(session)
    if window_days:
        result = await service.refresh_future_window(
            window_days,
            source="admin_schedule",
            reason="manual_snapshot_rebuild",
        )
    else:
        result = await service.rebuild_all_open_snapshots(
            source="admin_schedule",
            reason="manual_snapshot_rebuild",
        )
    await session.commit()
    return ApiResponse.ok(data=result)


@router.get(
    "/snapshots/observability",
    summary="查看排产快照观测信息",
    description="返回排产快照总体观测结果，包括快照数量、异常状态和最近刷新情况。",
    response_model=ApiResponse[SnapshotObservabilityResponse],
)
async def get_schedule_snapshot_observability(
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_schedule_manage_permission),
):
    service = ScheduleSnapshotRefreshService(session)
    return ApiResponse.ok(data=await service.get_observability_summary())
