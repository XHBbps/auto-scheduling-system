from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import CurrentUserIdentity, require_permission
from app.common.query_sort_utils import build_sort_expression, resolve_order_by
from app.common.response import ApiResponse
from app.database import get_session
from app.models.bom_relation import BomRelationSrc
from app.schemas.common import PageResult
from app.schemas.data_source_schemas import (
    BomRelationItemResponse,
    BomTreeChildrenResponse,
    BomTreeRootsResponse,
)

router = APIRouter(prefix="/api/data/bom-relations", tags=["外源数据-BOM物料清单"])

require_data_source_view_permission = require_permission("data_source.view")


def _serialize_bom_row(i: BomRelationSrc) -> dict:
    return {
        "id": i.id,
        "machine_material_no": i.machine_material_no,
        "machine_material_desc": i.machine_material_desc,
        "plant": i.plant,
        "material_no": i.material_no,
        "material_desc": i.material_desc,
        "bom_component_no": i.bom_component_no,
        "bom_component_desc": i.bom_component_desc,
        "part_type": i.part_type,
        "component_qty": float(i.component_qty) if i.component_qty else None,
        "bom_level": i.bom_level,
        "is_top_level": i.is_top_level,
        "is_self_made": i.is_self_made,
        "sync_time": i.sync_time.isoformat() if i.sync_time else None,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


def _parse_machine_material_nos(machine_material_no: str | None) -> list[str]:
    if not machine_material_no:
        return []

    normalized = machine_material_no.replace("，", ",").replace("\n", ",").replace(";", ",")
    values: list[str] = []
    for part in normalized.split(","):
        item = part.strip()
        if item and item not in values:
            values.append(item)
    return values


def _serialize_tree_node(row: BomRelationSrc, has_children: bool) -> dict:
    return {
        "id": row.id,
        "node_key": f"bom-row-{row.id}",
        "machine_material_no": row.machine_material_no,
        "plant": row.plant,
        "parent_material_no": row.material_no,
        "parent_material_desc": row.material_desc,
        "material_no": row.bom_component_no,
        "material_desc": row.bom_component_desc,
        "part_type": row.part_type,
        "component_qty": float(row.component_qty) if row.component_qty else None,
        "bom_level": row.bom_level,
        "is_top_level": row.is_top_level,
        "is_self_made": row.is_self_made,
        "sync_time": row.sync_time.isoformat() if row.sync_time else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "has_children": has_children,
        "children_loaded": False,
        "children": [],
    }


async def _query_has_children_material_nos(
    session: AsyncSession,
    machine_material_no: str,
    material_nos: list[str],
) -> set[str]:
    if not machine_material_no or not material_nos:
        return set()

    stmt = (
        select(BomRelationSrc.material_no)
        .where(
            and_(
                BomRelationSrc.machine_material_no == machine_material_no,
                BomRelationSrc.material_no.in_(material_nos),
            )
        )
        .distinct()
    )
    rows = (await session.execute(stmt)).scalars().all()
    return {item for item in rows if item}


async def _build_root_nodes(
    session: AsyncSession,
    machine_material_nos: list[str],
) -> list[dict]:
    base_stmt = select(
        BomRelationSrc.machine_material_no,
        func.min(BomRelationSrc.machine_material_desc).label("machine_material_desc"),
        func.min(BomRelationSrc.plant).label("plant"),
        func.max(BomRelationSrc.sync_time).label("latest_sync_time"),
        func.max(
            case(
                (BomRelationSrc.material_no == BomRelationSrc.machine_material_no, 1),
                else_=0,
            )
        ).label("has_children_flag"),
    )
    if machine_material_nos:
        base_stmt = base_stmt.where(BomRelationSrc.machine_material_no.in_(machine_material_nos))

    summary_rows = (
        await session.execute(
            base_stmt.group_by(BomRelationSrc.machine_material_no).order_by(BomRelationSrc.machine_material_no)
        )
    ).all()
    if not summary_rows:
        return []

    roots: list[dict] = []
    for machine_no, machine_desc, plant, latest_sync_time, has_children_flag in summary_rows:
        roots.append(
            {
                "id": 0,
                "node_key": f"bom-root-{machine_no}",
                "machine_material_no": machine_no,
                "plant": plant,
                "parent_material_no": None,
                "parent_material_desc": None,
                "material_no": machine_no,
                "material_desc": machine_desc,
                "part_type": "整机",
                "component_qty": 1,
                "bom_level": 0,
                "is_top_level": True,
                "is_self_made": True,
                "sync_time": latest_sync_time.isoformat() if latest_sync_time else None,
                "created_at": None,
                "has_children": bool(has_children_flag),
                "children_loaded": False,
                "children": [],
            }
        )

    return roots


@router.get(
    "",
    summary="查询 BOM 明细列表",
    description="分页查询 BOM 源数据明细，可按整机物料、父项物料、子件物料和零件类型筛选。",
    response_model=ApiResponse[PageResult[BomRelationItemResponse]],
)
async def list_bom_relations(
    machine_material_no: str | None = None,
    material_no: str | None = None,
    bom_component_no: str | None = None,
    part_type: str | None = None,
    page_no: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: str | None = None,
    sort_order: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_data_source_view_permission),
):
    conditions = []
    if machine_material_no:
        conditions.append(BomRelationSrc.machine_material_no.ilike(f"%{machine_material_no}%"))
    if material_no:
        conditions.append(BomRelationSrc.material_no.ilike(f"%{material_no}%"))
    if bom_component_no:
        conditions.append(BomRelationSrc.bom_component_no.ilike(f"%{bom_component_no}%"))
    if part_type:
        conditions.append(BomRelationSrc.part_type.ilike(f"%{part_type}%"))

    where = and_(*conditions) if conditions else True

    count_stmt = select(func.count()).select_from(BomRelationSrc).where(where)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = (
        select(BomRelationSrc)
        .where(where)
        .order_by(
            *resolve_order_by(
                sort_expression=build_sort_expression(
                    sort_field=sort_field,
                    sort_order=sort_order,
                    allowed_fields={
                        "id": BomRelationSrc.id,
                        "machine_material_no": BomRelationSrc.machine_material_no,
                        "machine_material_desc": BomRelationSrc.machine_material_desc,
                        "plant": BomRelationSrc.plant,
                        "material_no": BomRelationSrc.material_no,
                        "material_desc": BomRelationSrc.material_desc,
                        "bom_component_no": BomRelationSrc.bom_component_no,
                        "bom_component_desc": BomRelationSrc.bom_component_desc,
                        "part_type": BomRelationSrc.part_type,
                        "component_qty": BomRelationSrc.component_qty,
                        "bom_level": BomRelationSrc.bom_level,
                        "is_top_level": BomRelationSrc.is_top_level,
                        "is_self_made": BomRelationSrc.is_self_made,
                        "sync_time": BomRelationSrc.sync_time,
                    },
                ),
                default_order_by=[desc(BomRelationSrc.id)],
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
            "items": [_serialize_bom_row(i) for i in items],
        }
    )


@router.get(
    "/tree",
    summary="查询 BOM 树根节点",
    description="按整机物料号返回 BOM 树根节点与简要信息。",
    response_model=ApiResponse[BomTreeRootsResponse],
)
async def get_bom_tree(
    machine_material_no: str | None = Query(None, description="整机物料号，支持英文逗号、中文逗号、换行分隔多个值。"),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_data_source_view_permission),
):
    machine_material_nos = _parse_machine_material_nos(machine_material_no)
    total = len(machine_material_nos)
    roots = await _build_root_nodes(session, machine_material_nos)
    if not machine_material_nos:
        total = len(roots)

    return ApiResponse.ok(
        data={
            "machine_material_no": machine_material_no,
            "machine_material_nos": machine_material_nos,
            "total": total,
            "root_count": len(roots),
            "root": roots[0] if len(roots) == 1 else None,
            "roots": roots,
        }
    )


@router.get(
    "/tree/children",
    summary="查询 BOM 树子节点",
    description="按父节点懒加载 BOM 子节点，支持分页偏移。",
    response_model=ApiResponse[BomTreeChildrenResponse],
)
async def get_bom_tree_children(
    machine_material_no: str = Query(..., description="所属整机物料号，用于限定当前 BOM 树范围。"),
    parent_material_no: str = Query(..., description="父级物料号，用于按节点懒加载其直接子节点。"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    _: CurrentUserIdentity = Depends(require_data_source_view_permission),
):
    total_stmt = (
        select(func.count())
        .select_from(BomRelationSrc)
        .where(
            and_(
                BomRelationSrc.machine_material_no == machine_material_no,
                BomRelationSrc.material_no == parent_material_no,
            )
        )
    )
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = (
        select(BomRelationSrc)
        .where(
            and_(
                BomRelationSrc.machine_material_no == machine_material_no,
                BomRelationSrc.material_no == parent_material_no,
            )
        )
        .order_by(BomRelationSrc.bom_level, BomRelationSrc.id)
    )
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    rows = list((await session.execute(stmt)).scalars().all())

    child_material_nos = [row.bom_component_no for row in rows if row.bom_component_no]
    has_children_material_nos = await _query_has_children_material_nos(
        session,
        machine_material_no=machine_material_no,
        material_nos=child_material_nos,
    )

    items = [
        _serialize_tree_node(
            row,
            has_children=(row.bom_component_no in has_children_material_nos),
        )
        for row in rows
    ]

    return ApiResponse.ok(
        data={
            "machine_material_no": machine_material_no,
            "parent_material_no": parent_material_no,
            "total": total,
            "count": len(items),
            "offset": offset,
            "limit": limit,
            "has_more": (offset + len(items)) < total,
            "next_offset": offset + len(items),
            "items": items,
        }
    )
