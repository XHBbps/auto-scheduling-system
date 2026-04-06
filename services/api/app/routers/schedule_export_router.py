from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.database import get_session
from app.services.schedule_export_service import ExportService

router = APIRouter(prefix="/api/exports", tags=["导出"])

require_export_view_permission = require_permission("export.view")


def _build_content_disposition(filename: str) -> str:
    encoded = quote(filename)
    fallback_name = filename.encode("ascii", errors="ignore").decode("ascii") or "export"
    return f"attachment; filename={fallback_name}; filename*=UTF-8''{encoded}"


@router.get(
    "/machine-schedules",
    summary="导出整机排产列表",
    description="按当前筛选条件导出整机排产结果，支持 xlsx 和 csv 两种格式，成功时直接返回文件流。",
    response_description="导出文件流，支持 xlsx / csv",
)
async def export_machine_schedules(
    export_format: str = Query(
        "xlsx", pattern="^(xlsx|csv)$", description="导出文件格式；xlsx 为 Excel，csv 为文本格式。"
    ),
    order_line_id: int | None = None,
    contract_no: str | None = None,
    customer_name: str | None = None,
    product_series: str | None = None,
    product_model: str | None = None,
    plant: str | None = None,
    order_no: str | None = None,
    schedule_status: str | None = None,
    assembly_name: str | None = None,
    part_material_no: str | None = None,
    key_part_name: str | None = None,
    key_part_material_no: str | None = None,
    warning_level: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_field: str | None = None,
    sort_order: str | None = Query(None, pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_export_view_permission),
) -> StreamingResponse:
    service = ExportService(session)
    buf, filename, media_type = await service.export_machine_schedules(
        export_format=export_format,
        order_line_id=order_line_id,
        contract_no=contract_no,
        customer_name=customer_name,
        product_series=product_series,
        product_model=product_model,
        plant=plant,
        order_no=order_no,
        schedule_status=schedule_status,
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
    return StreamingResponse(
        buf,
        media_type=media_type,
        headers={"Content-Disposition": _build_content_disposition(filename)},
    )


@router.get(
    "/part-schedules",
    summary="导出零件排产列表",
    description="按当前筛选条件导出零件排产结果，支持 xlsx 和 csv 两种格式，成功时直接返回文件流。",
    response_description="导出文件流，支持 xlsx / csv",
)
async def export_part_schedules(
    export_format: str = Query(
        "xlsx", pattern="^(xlsx|csv)$", description="导出文件格式；xlsx 为 Excel，csv 为文本格式。"
    ),
    order_line_id: int | None = None,
    contract_no: str | None = None,
    customer_name: str | None = None,
    product_series: str | None = None,
    product_model: str | None = None,
    plant: str | None = None,
    order_no: str | None = None,
    schedule_status: str | None = None,
    warning_level: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_field: str | None = None,
    sort_order: str | None = Query(None, pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_export_view_permission),
) -> StreamingResponse:
    service = ExportService(session)
    buf, filename, media_type = await service.export_part_schedules(
        export_format=export_format,
        order_line_id=order_line_id,
        contract_no=contract_no,
        customer_name=customer_name,
        product_series=product_series,
        product_model=product_model,
        plant=plant,
        order_no=order_no,
        schedule_status=schedule_status,
        warning_level=warning_level,
        date_from=date_from,
        date_to=date_to,
        sort_field=sort_field,
        sort_order=sort_order,
    )
    return StreamingResponse(
        buf,
        media_type=media_type,
        headers={"Content-Disposition": _build_content_disposition(filename)},
    )
