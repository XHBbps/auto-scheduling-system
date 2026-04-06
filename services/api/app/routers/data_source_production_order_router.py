from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.common.query_sort_utils import build_sort_expression, resolve_order_by
from app.common.response import ApiResponse
from app.database import get_session
from app.models.production_order import ProductionOrderHistorySrc
from app.schemas.common import PageResult
from app.schemas.data_source_schemas import ProductionOrderHistoryItemResponse

router = APIRouter(prefix="/api/data/production-orders", tags=["外源数据-生产订单历史"])

require_data_source_view_permission = require_permission("data_source.view")


@router.get(
    "",
    summary="查询生产订单历史",
    description="按生产订单号、物料号、机型和订单状态等条件分页查询生产订单历史源数据，供排产回溯与历史订单核对使用。",
    response_model=ApiResponse[PageResult[ProductionOrderHistoryItemResponse]],
)
async def list_production_orders(
    production_order_no: str | None = None,
    material_no: str | None = None,
    machine_model: str | None = None,
    order_status: str | None = None,
    page_no: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: str | None = None,
    sort_order: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_data_source_view_permission),
):
    conditions = []
    if production_order_no:
        conditions.append(ProductionOrderHistorySrc.production_order_no.ilike(f"%{production_order_no}%"))
    if material_no:
        conditions.append(ProductionOrderHistorySrc.material_no.ilike(f"%{material_no}%"))
    if machine_model:
        conditions.append(ProductionOrderHistorySrc.machine_model.ilike(f"%{machine_model}%"))
    if order_status:
        conditions.append(ProductionOrderHistorySrc.order_status == order_status)

    where = and_(*conditions) if conditions else True

    count_stmt = select(func.count()).select_from(ProductionOrderHistorySrc).where(where)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = (
        select(ProductionOrderHistorySrc)
        .where(where)
        .order_by(
            *resolve_order_by(
                sort_expression=build_sort_expression(
                    sort_field=sort_field,
                    sort_order=sort_order,
                    allowed_fields={
                        "id": ProductionOrderHistorySrc.id,
                        "production_order_no": ProductionOrderHistorySrc.production_order_no,
                        "material_no": ProductionOrderHistorySrc.material_no,
                        "material_desc": ProductionOrderHistorySrc.material_desc,
                        "machine_model": ProductionOrderHistorySrc.machine_model,
                        "plant": ProductionOrderHistorySrc.plant,
                        "processing_dept": ProductionOrderHistorySrc.processing_dept,
                        "production_qty": ProductionOrderHistorySrc.production_qty,
                        "order_status": ProductionOrderHistorySrc.order_status,
                        "start_time_actual": ProductionOrderHistorySrc.start_time_actual,
                        "finish_time_actual": ProductionOrderHistorySrc.finish_time_actual,
                        "sales_order_no": ProductionOrderHistorySrc.sales_order_no,
                        "created_at": ProductionOrderHistorySrc.created_at,
                    },
                ),
                default_order_by=[desc(ProductionOrderHistorySrc.id)],
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
                    "production_order_no": i.production_order_no,
                    "material_no": i.material_no,
                    "material_desc": i.material_desc,
                    "machine_model": i.machine_model,
                    "plant": i.plant,
                    "processing_dept": i.processing_dept,
                    "start_time_actual": i.start_time_actual.isoformat() if i.start_time_actual else None,
                    "finish_time_actual": i.finish_time_actual.isoformat() if i.finish_time_actual else None,
                    "production_qty": float(i.production_qty) if i.production_qty else None,
                    "order_status": i.order_status,
                    "sales_order_no": i.sales_order_no,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in items
            ],
        }
    )
