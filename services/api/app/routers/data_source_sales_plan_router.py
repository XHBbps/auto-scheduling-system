from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.common.query_sort_utils import build_sort_expression, resolve_order_by
from app.common.response import ApiResponse
from app.database import get_session
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.schemas.common import PageResult
from app.schemas.data_source_schemas import SalesPlanOrderItemResponse, SalesPlanOrgFilterOptionsResponse

router = APIRouter(prefix="/api/data/sales-plan-orders", tags=["外源数据-销售计划订单行"])

require_data_source_view_permission = require_permission("data_source.view")


async def _load_distinct_trimmed_values(
    session: AsyncSession,
    column,
) -> list[str]:
    normalized = func.trim(column)
    stmt = select(distinct(normalized)).where(column.isnot(None), func.length(normalized) > 0).order_by(normalized)
    result = await session.execute(stmt)
    return [value for value in result.scalars().all() if value]


@router.get(
    "/options/org-filters",
    summary="获取销售组织筛选项",
    description="返回销售计划源数据中的事业部、销售分公司和销售子公司去重筛选项。",
    response_model=ApiResponse[SalesPlanOrgFilterOptionsResponse],
)
async def get_sales_plan_org_filter_options(
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_data_source_view_permission),
):
    business_groups = await _load_distinct_trimmed_values(session, SalesPlanOrderLineSrc.business_group)
    sales_branch_companies = await _load_distinct_trimmed_values(session, SalesPlanOrderLineSrc.sales_branch_company)
    sales_sub_branches = await _load_distinct_trimmed_values(session, SalesPlanOrderLineSrc.sales_sub_branch)
    return ApiResponse.ok(
        data={
            "business_groups": business_groups,
            "sales_branch_companies": sales_branch_companies,
            "sales_sub_branches": sales_sub_branches,
        }
    )


@router.get(
    "",
    summary="查询销售计划订单行",
    description="分页查询销售计划源订单行，可按合同、客户、机型、物料和销售组织维度筛选。",
    response_model=ApiResponse[PageResult[SalesPlanOrderItemResponse]],
)
async def list_sales_plan_orders(
    contract_no: str | None = None,
    customer_name: str | None = None,
    product_series: str | None = None,
    product_model: str | None = None,
    material_no: str | None = None,
    business_group: str | None = None,
    sales_branch_company: str | None = None,
    sales_sub_branch: str | None = None,
    page_no: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: str | None = None,
    sort_order: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_data_source_view_permission),
):
    conditions = []
    if contract_no:
        conditions.append(SalesPlanOrderLineSrc.contract_no.ilike(f"%{contract_no}%"))
    if customer_name:
        conditions.append(SalesPlanOrderLineSrc.customer_name.ilike(f"%{customer_name}%"))
    if product_series:
        conditions.append(SalesPlanOrderLineSrc.product_series.ilike(f"%{product_series}%"))
    if product_model:
        conditions.append(SalesPlanOrderLineSrc.product_model.ilike(f"%{product_model}%"))
    if material_no:
        conditions.append(SalesPlanOrderLineSrc.material_no.ilike(f"%{material_no}%"))
    if business_group:
        conditions.append(SalesPlanOrderLineSrc.business_group.ilike(f"%{business_group}%"))
    if sales_branch_company:
        conditions.append(SalesPlanOrderLineSrc.sales_branch_company.ilike(f"%{sales_branch_company}%"))
    if sales_sub_branch:
        conditions.append(SalesPlanOrderLineSrc.sales_sub_branch.ilike(f"%{sales_sub_branch}%"))

    where = and_(*conditions) if conditions else True

    count_stmt = select(func.count()).select_from(SalesPlanOrderLineSrc).where(where)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = (
        select(SalesPlanOrderLineSrc)
        .where(where)
        .order_by(
            *resolve_order_by(
                sort_expression=build_sort_expression(
                    sort_field=sort_field,
                    sort_order=sort_order,
                    allowed_fields={
                        "id": SalesPlanOrderLineSrc.id,
                        "contract_no": SalesPlanOrderLineSrc.contract_no,
                        "customer_name": SalesPlanOrderLineSrc.customer_name,
                        "product_series": SalesPlanOrderLineSrc.product_series,
                        "product_model": SalesPlanOrderLineSrc.product_model,
                        "product_name": SalesPlanOrderLineSrc.product_name,
                        "material_no": SalesPlanOrderLineSrc.material_no,
                        "quantity": SalesPlanOrderLineSrc.quantity,
                        "line_total_amount": SalesPlanOrderLineSrc.line_total_amount,
                        "order_date": SalesPlanOrderLineSrc.order_date,
                        "order_type": SalesPlanOrderLineSrc.order_type,
                        "business_group": SalesPlanOrderLineSrc.business_group,
                        "custom_no": SalesPlanOrderLineSrc.custom_no,
                        "sales_person_name": SalesPlanOrderLineSrc.sales_person_name,
                        "sales_branch_company": SalesPlanOrderLineSrc.sales_branch_company,
                        "sales_sub_branch": SalesPlanOrderLineSrc.sales_sub_branch,
                        "drawing_released": SalesPlanOrderLineSrc.drawing_released,
                        "confirmed_delivery_date": SalesPlanOrderLineSrc.confirmed_delivery_date,
                        "order_no": SalesPlanOrderLineSrc.order_no,
                        "sap_code": SalesPlanOrderLineSrc.sap_code,
                        "sap_line_no": SalesPlanOrderLineSrc.sap_line_no,
                        "custom_requirement": SalesPlanOrderLineSrc.custom_requirement,
                        "review_comment": SalesPlanOrderLineSrc.review_comment,
                        "created_at": SalesPlanOrderLineSrc.created_at,
                    },
                ),
                default_order_by=[desc(SalesPlanOrderLineSrc.id)],
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
                    "contract_no": i.contract_no,
                    "customer_name": i.customer_name,
                    "product_series": i.product_series,
                    "product_model": i.product_model,
                    "product_name": i.product_name,
                    "material_no": i.material_no,
                    "quantity": float(i.quantity) if i.quantity else None,
                    "line_total_amount": float(i.line_total_amount) if i.line_total_amount else None,
                    "confirmed_delivery_date": i.confirmed_delivery_date.isoformat()
                    if i.confirmed_delivery_date
                    else None,
                    "delivery_date": i.delivery_date.isoformat() if i.delivery_date else None,
                    "order_type": i.order_type,
                    "business_group": i.business_group,
                    "custom_no": i.custom_no,
                    "sales_person_name": i.sales_person_name,
                    "order_date": i.order_date.isoformat() if i.order_date else None,
                    "sales_branch_company": i.sales_branch_company,
                    "sales_sub_branch": i.sales_sub_branch,
                    "drawing_released": i.drawing_released,
                    "drawing_release_date": i.drawing_release_date.isoformat() if i.drawing_release_date else None,
                    "order_no": i.order_no,
                    "sap_code": i.sap_code,
                    "sap_line_no": i.sap_line_no,
                    "custom_requirement": i.custom_requirement,
                    "review_comment": i.review_comment,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in items
            ],
        }
    )
