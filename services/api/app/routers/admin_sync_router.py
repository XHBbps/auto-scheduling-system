import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.common.enums import BomBackfillQueueStatus
from app.common.exceptions import BizException, ErrorCode
from app.common.response import ApiResponse
from app.database import get_session
from app.models.bom_backfill_queue import BomBackfillQueue
from app.repository.bom_backfill_queue_repo import BomBackfillQueueRepo
from app.repository.sales_plan_repo import SalesPlanRepo
from app.schemas.admin_schemas import (
    BomBackfillQueuePageResponse,
    BomBackfillQueueRetryRequest,
    RetryQueueResponse,
    SyncBomRequest,
    SyncObservabilityResponse,
    SyncResearchRequest,
    SyncSalesPlanRequest,
    SyncScheduleRequest,
    SyncSchedulerStatusResponse,
    SyncTriggerResponse,
)
from app.services.sync_job_observability_service import SyncJobObservabilityService
from app.sync.bom_backfill_queue_service import serialize_bom_backfill_queue_item
from app.sync.manual_sync_job_service import ManualSyncTaskService
from app.sync.sales_plan_filters import (
    build_sales_plan_filter_window,
    format_sales_plan_filter_window,
)
from app.sync.sync_job_message_templates import (
    bom_trigger_message,
    production_order_trigger_message,
    research_trigger_message,
    sales_plan_trigger_message,
)
from app.sync_scheduler import SyncSchedulerControlService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/sync", tags=["手动同步"])

require_sync_manage_permission = require_permission("sync.manage")


def _get_manual_sync_service() -> ManualSyncTaskService:
    return ManualSyncTaskService()


@router.post(
    "/sales-plan",
    summary="手动同步销售计划",
    description="创建销售计划同步任务，后台异步执行。",
    response_model=ApiResponse[SyncTriggerResponse],
)
async def sync_sales_plan(
    req: SyncSalesPlanRequest,
    session: AsyncSession = Depends(get_session),
    admin_identity: CurrentUserIdentity = Depends(require_sync_manage_permission),
) -> ApiResponse[Any]:
    try:
        filter_window = build_sales_plan_filter_window(
            start_time=req.start_time,
            end_time=req.end_time,
        )
        manual_sync_service = _get_manual_sync_service()
        job_id, status, created = await manual_sync_service.enqueue_sales_plan(
            session,
            operator_name=admin_identity.operator_name,
            message=f"手动触发销售计划同步，筛选条件：{format_sales_plan_filter_window(filter_window)}。",
            filter_payload=filter_window.filter_payload,
        )
        return ApiResponse.ok(
            data={
                "job_id": job_id,
                "status": status,
                "message": sales_plan_trigger_message(created=created),
            }
        )
    except ValueError as exc:
        raise BizException(ErrorCode.BIZ_VALIDATION_FAILED, str(exc)) from exc
    except BizException:
        raise
    except Exception as e:
        logger.error("Sales plan sync trigger failed: %s", e, exc_info=True)
        raise BizException(ErrorCode.EXTERNAL_API_FAILED, "销售计划同步触发失败，请稍后重试") from e


@router.post(
    "/bom",
    summary="手动同步 BOM",
    description="按物料号或订单行触发 BOM 同步。",
    response_model=ApiResponse[SyncTriggerResponse],
)
async def sync_bom(
    req: SyncBomRequest,
    session: AsyncSession = Depends(get_session),
    admin_identity: CurrentUserIdentity = Depends(require_sync_manage_permission),
) -> ApiResponse[Any]:
    try:
        items: list[tuple[str, str]] = []
        if req.material_no:
            if not req.plant:
                return ApiResponse.ok(
                    data={
                        "job_id": None,
                        "status": "noop",
                        "message": "请输入工厂后再执行 BOM 手动同步。",
                    }
                )
            items.append((req.material_no, req.plant))
        elif req.order_line_ids:
            repo = SalesPlanRepo(session)
            for order in await repo.find_by_ids(req.order_line_ids):
                if order and order.material_no:
                    items.append((order.material_no, order.delivery_plant or "1000"))

        if not items:
            return ApiResponse.ok(
                data={
                    "job_id": None,
                    "status": "noop",
                    "message": "未找到可执行 BOM 同步的物料。",
                }
            )

        manual_sync_service = _get_manual_sync_service()
        job_id, status, created = await manual_sync_service.enqueue_bom(
            session,
            operator_name=admin_identity.operator_name,
            message=f"手动触发 BOM 同步，请求物料 {len(items)} 个。",
            items=items,
        )
        return ApiResponse.ok(
            data={
                "job_id": job_id,
                "status": status,
                "message": bom_trigger_message(created=created),
            }
        )
    except BizException:
        raise
    except Exception as e:
        logger.error("BOM sync trigger failed: %s", e, exc_info=True)
        raise BizException(ErrorCode.EXTERNAL_API_FAILED, "BOM 同步触发失败，请稍后重试") from e


@router.post(
    "/production-orders",
    summary="手动同步生产订单",
    description="创建生产订单同步任务，后台异步拉取并写入生产订单历史数据。",
    response_model=ApiResponse[SyncTriggerResponse],
)
async def sync_production_orders(
    session: AsyncSession = Depends(get_session),
    admin_identity: CurrentUserIdentity = Depends(require_sync_manage_permission),
) -> ApiResponse[Any]:
    try:
        manual_sync_service = _get_manual_sync_service()
        job_id, status, created = await manual_sync_service.enqueue_production_orders(
            session,
            operator_name=admin_identity.operator_name,
            message="手动触发生产订单同步，任务已进入后台执行。",
        )
        return ApiResponse.ok(
            data={
                "job_id": job_id,
                "status": status,
                "message": production_order_trigger_message(created=created),
            }
        )
    except BizException:
        raise
    except Exception as e:
        logger.error("Production order sync trigger failed: %s", e, exc_info=True)
        raise BizException(ErrorCode.EXTERNAL_API_FAILED, "生产订单同步触发失败，请稍后重试") from e


@router.post(
    "/research",
    summary="手动同步研究所数据",
    description="创建研究所数据同步任务，可按订单号模式缩小同步范围，任务在后台异步执行。",
    response_model=ApiResponse[SyncTriggerResponse],
)
async def sync_research(
    req: SyncResearchRequest,
    session: AsyncSession = Depends(get_session),
    admin_identity: CurrentUserIdentity = Depends(require_sync_manage_permission),
) -> ApiResponse[Any]:
    try:
        manual_sync_service = _get_manual_sync_service()
        order_no_filter = req.order_no if req.mode == "by_order_no" else None
        job_id, status, created = await manual_sync_service.enqueue_research(
            session,
            operator_name=admin_identity.operator_name,
            message="手动触发研究所数据同步，任务已进入后台执行。",
            order_no_filter=order_no_filter,
        )
        return ApiResponse.ok(
            data={
                "job_id": job_id,
                "status": status,
                "message": research_trigger_message(created=created),
            }
        )
    except BizException:
        raise
    except Exception as e:
        logger.error("Research sync trigger failed: %s", e, exc_info=True)
        raise BizException(ErrorCode.EXTERNAL_API_FAILED, "研究所数据同步触发失败，请稍后重试") from e


@router.get(
    "/schedule",
    summary="查看自动同步调度状态",
    description="返回自动同步调度器当前启停状态、下次执行时间和内部观测信息。",
    response_model=ApiResponse[SyncSchedulerStatusResponse],
)
async def get_sync_schedule(
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_sync_manage_permission),
) -> ApiResponse[Any]:
    service = SyncSchedulerControlService(session)
    return ApiResponse.ok(data=await service.get_status())


@router.post(
    "/schedule",
    summary="控制自动同步调度开关",
    description="启用或停用自动同步调度器，适合在维护窗口或问题排查时临时调整自动任务。",
    response_model=ApiResponse[SyncSchedulerStatusResponse],
)
async def control_sync_schedule(
    req: SyncScheduleRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_sync_manage_permission),
) -> ApiResponse[Any]:
    service = SyncSchedulerControlService(session)
    return ApiResponse.ok(data=await service.set_enabled(req.enabled, updated_by="api"))


@router.get(
    "/observability",
    summary="查看同步观测摘要",
    description="返回同步任务总体观测摘要，包括运行中任务、最近失败、超时和回收状态等信息。",
    response_model=ApiResponse[SyncObservabilityResponse],
)
async def get_sync_observability(
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_sync_manage_permission),
) -> ApiResponse[Any]:
    return ApiResponse.ok(data=await SyncJobObservabilityService(session).get_summary())


@router.get(
    "/bom-backfill-queue",
    summary="查询 BOM 补数队列",
    description="分页查询 BOM 补数队列，便于排查缺 BOM、重试等待和失败记录。",
    response_model=ApiResponse[BomBackfillQueuePageResponse],
)
async def list_bom_backfill_queue(
    page_no: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    failure_kind: str | None = None,
    material_no: str | None = None,
    source: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_sync_manage_permission),
) -> ApiResponse[Any]:
    repo = BomBackfillQueueRepo(session)
    total, items = await repo.list_page(
        page_no=page_no,
        page_size=page_size,
        status=status,
        failure_kind=failure_kind,
        material_no=material_no,
        source=source,
    )
    return ApiResponse.ok(
        data={
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
            "items": [serialize_bom_backfill_queue_item(item) for item in items],
        }
    )


@router.post(
    "/bom-backfill-queue/retry",
    summary="重试 BOM 补数队列记录",
    description="将指定 BOM 补数队列记录重置为待处理状态，供后续补数任务重新消费。",
    response_model=ApiResponse[RetryQueueResponse],
)
async def retry_bom_backfill_queue_items(
    req: BomBackfillQueueRetryRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_sync_manage_permission),
) -> ApiResponse[Any]:
    items = (await session.execute(select(BomBackfillQueue).where(BomBackfillQueue.id.in_(req.ids)))).scalars().all()
    changed = 0
    for item in items:
        if item.status not in {
            BomBackfillQueueStatus.RETRY_WAIT.value,
            BomBackfillQueueStatus.FAILED.value,
        }:
            continue
        item.status = BomBackfillQueueStatus.PENDING.value
        item.next_retry_at = None
        item.failure_kind = None
        item.last_error = None
        changed += 1
    await session.commit()
    return ApiResponse.ok(
        data={
            "updated_count": changed,
            "message": f"已重置 {changed} 条 BOM 补数队列记录。",
        }
    )
