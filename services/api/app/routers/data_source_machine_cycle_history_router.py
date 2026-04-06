from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.common.query_sort_utils import build_sort_expression, resolve_order_by
from app.common.response import ApiResponse
from app.database import get_session
from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.schemas.common import PageResult
from app.schemas.data_source_schemas import MachineCycleHistoryItemResponse

router = APIRouter(prefix="/api/data/machine-cycle-history", tags=["外源数据-整机周期历史"])

require_data_source_view_permission = require_permission("data_source.view")


@router.get(
    "",
    summary="查询整机周期历史",
    description="按机型、产品系列、合同号和订单号等条件分页查询整机周期历史源数据，供基准回溯和周期对比使用。",
    response_model=ApiResponse[PageResult[MachineCycleHistoryItemResponse]],
)
async def list_machine_cycle_history(
    machine_model: str | None = None,
    product_series: str | None = None,
    contract_no: str | None = None,
    order_no: str | None = None,
    page_no: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: str | None = None,
    sort_order: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_data_source_view_permission),
):
    conditions = []
    if machine_model:
        conditions.append(MachineCycleHistorySrc.machine_model.ilike(f"%{machine_model}%"))
    if product_series:
        conditions.append(MachineCycleHistorySrc.product_series.ilike(f"%{product_series}%"))
    if contract_no:
        conditions.append(MachineCycleHistorySrc.contract_no.ilike(f"%{contract_no}%"))
    if order_no:
        conditions.append(MachineCycleHistorySrc.order_no.ilike(f"%{order_no}%"))

    where = and_(*conditions) if conditions else True

    count_stmt = select(func.count()).select_from(MachineCycleHistorySrc).where(where)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = (
        select(MachineCycleHistorySrc)
        .where(where)
        .order_by(
            *resolve_order_by(
                sort_expression=build_sort_expression(
                    sort_field=sort_field,
                    sort_order=sort_order,
                    allowed_fields={
                        "id": MachineCycleHistorySrc.id,
                        "machine_model": MachineCycleHistorySrc.machine_model,
                        "product_series": MachineCycleHistorySrc.product_series,
                        "order_qty": MachineCycleHistorySrc.order_qty,
                        "cycle_days": MachineCycleHistorySrc.cycle_days,
                        "order_type": MachineCycleHistorySrc.order_type,
                        "contract_no": MachineCycleHistorySrc.contract_no,
                        "order_no": MachineCycleHistorySrc.order_no,
                        "customer_name": MachineCycleHistorySrc.customer_name,
                        "drawing_release_date": MachineCycleHistorySrc.drawing_release_date,
                        "inspection_date": MachineCycleHistorySrc.inspection_date,
                        "created_at": MachineCycleHistorySrc.created_at,
                    },
                ),
                default_order_by=[desc(MachineCycleHistorySrc.id)],
            )
        )
        .offset((page_no - 1) * page_size)
        .limit(page_size)
    )
    items = (await session.execute(stmt)).scalars().all()

    return ApiResponse.ok(
        data={
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
            "items": [
                {
                    "id": i.id,
                    "detail_id": i.detail_id,
                    "machine_model": i.machine_model,
                    "product_series": i.product_series,
                    "order_qty": float(i.order_qty) if i.order_qty else None,
                    "drawing_release_date": i.drawing_release_date.isoformat() if i.drawing_release_date else None,
                    "inspection_date": i.inspection_date.isoformat() if i.inspection_date else None,
                    "customer_name": i.customer_name,
                    "contract_no": i.contract_no,
                    "order_no": i.order_no,
                    "order_type": i.order_type,
                    "cycle_days": float(i.cycle_days) if i.cycle_days else None,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in items
            ],
        }
    )
