import pytest
from decimal import Decimal
from datetime import datetime

from app.models.bom_relation import BomRelationSrc


@pytest.mark.asyncio
async def test_get_bom_tree(app_client, db_session):
    rows = [
        BomRelationSrc(
            machine_material_no="MACH001",
            machine_material_desc="整机A",
            plant="1000",
            material_no="MACH001",
            material_desc="整机A",
            bom_component_no="ASM001",
            bom_component_desc="机身体总成",
            part_type="自产件",
            component_qty=Decimal("1"),
            bom_level=1,
            is_top_level=True,
            is_self_made=True,
            sync_time=datetime(2026, 3, 18, 10, 0, 0),
        ),
        BomRelationSrc(
            machine_material_no="MACH001",
            machine_material_desc="整机A",
            plant="1000",
            material_no="ASM001",
            material_desc="机身体总成",
            bom_component_no="PART001",
            bom_component_desc="机身体焊接件",
            part_type="自产件",
            component_qty=Decimal("1"),
            bom_level=2,
            is_top_level=False,
            is_self_made=True,
            sync_time=datetime(2026, 3, 18, 10, 0, 0),
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()

    resp = await app_client.get("/api/data/bom-relations/tree", params={"machine_material_no": "MACH001"})
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["total"] == 1
    root = body["data"]["root"]
    assert root["material_no"] == "MACH001"
    assert root["has_children"] is True
    assert root["children_loaded"] is False
    assert root["children"] == []
    assert body["data"]["root_count"] == 1
    assert len(body["data"]["roots"]) == 1


@pytest.mark.asyncio
async def test_get_bom_tree_multi_roots(app_client, db_session):
    rows = [
        BomRelationSrc(
            machine_material_no="MACH001",
            machine_material_desc="整机A",
            plant="1000",
            material_no="MACH001",
            material_desc="整机A",
            bom_component_no="ASM001",
            bom_component_desc="机身总成",
            part_type="自产件",
            component_qty=Decimal("1"),
            bom_level=1,
            is_top_level=True,
            is_self_made=True,
            sync_time=datetime(2026, 3, 18, 10, 0, 0),
        ),
        BomRelationSrc(
            machine_material_no="MACH002",
            machine_material_desc="整机B",
            plant="1000",
            material_no="MACH002",
            material_desc="整机B",
            bom_component_no="ASM002",
            bom_component_desc="传动总成",
            part_type="外购件",
            component_qty=Decimal("2"),
            bom_level=1,
            is_top_level=True,
            is_self_made=False,
            sync_time=datetime(2026, 3, 18, 11, 0, 0),
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()

    resp = await app_client.get(
        "/api/data/bom-relations/tree",
        params={"machine_material_no": "MACH001,MACH002"},
    )
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["total"] == 2
    assert body["data"]["root_count"] == 2
    assert body["data"]["root"] is None
    roots = body["data"]["roots"]
    assert len(roots) == 2
    assert roots[0]["material_no"] == "MACH001"
    assert roots[1]["material_no"] == "MACH002"
    assert roots[0]["children_loaded"] is False
    assert roots[1]["children_loaded"] is False


@pytest.mark.asyncio
async def test_get_bom_tree_empty_query_returns_all_roots(app_client, db_session):
    rows = [
        BomRelationSrc(
            machine_material_no="MACH001",
            machine_material_desc="整机A",
            plant="1000",
            material_no="MACH001",
            material_desc="整机A",
            bom_component_no="ASM001",
            bom_component_desc="机身总成",
            part_type="自产件",
            component_qty=Decimal("1"),
            bom_level=1,
            is_top_level=True,
            is_self_made=True,
            sync_time=datetime(2026, 3, 18, 10, 0, 0),
        ),
        BomRelationSrc(
            machine_material_no="MACH002",
            machine_material_desc="整机B",
            plant="1000",
            material_no="MACH002",
            material_desc="整机B",
            bom_component_no="ASM002",
            bom_component_desc="传动总成",
            part_type="外购件",
            component_qty=Decimal("2"),
            bom_level=1,
            is_top_level=True,
            is_self_made=False,
            sync_time=datetime(2026, 3, 18, 11, 0, 0),
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()

    resp = await app_client.get("/api/data/bom-relations/tree")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["machine_material_nos"] == []
    assert body["data"]["total"] == 2
    assert body["data"]["root_count"] == 2
    assert body["data"]["root"] is None
    roots = body["data"]["roots"]
    assert [item["material_no"] for item in roots] == ["MACH001", "MACH002"]
    assert all(item["children"] == [] for item in roots)
    assert all(item["children_loaded"] is False for item in roots)


@pytest.mark.asyncio
async def test_get_bom_tree_by_multiple_machine_material_nos(app_client, db_session):
    rows = [
        BomRelationSrc(
            machine_material_no="MACH001",
            machine_material_desc="整机A",
            plant="1000",
            material_no="MACH001",
            material_desc="整机A",
            bom_component_no="ASM001",
            bom_component_desc="机身总成",
            part_type="自产件",
            component_qty=Decimal("1"),
            bom_level=1,
            is_top_level=True,
            is_self_made=True,
            sync_time=datetime(2026, 3, 18, 10, 0, 0),
        ),
        BomRelationSrc(
            machine_material_no="MACH002",
            machine_material_desc="整机B",
            plant="1000",
            material_no="MACH002",
            material_desc="整机B",
            bom_component_no="ASM002",
            bom_component_desc="传动总成",
            part_type="外购件",
            component_qty=Decimal("2"),
            bom_level=1,
            is_top_level=True,
            is_self_made=False,
            sync_time=datetime(2026, 3, 18, 11, 0, 0),
        ),
        BomRelationSrc(
            machine_material_no="MACH003",
            machine_material_desc="整机C",
            plant="1000",
            material_no="MACH003",
            material_desc="整机C",
            bom_component_no="ASM003",
            bom_component_desc="电气总成",
            part_type="虚拟件",
            component_qty=Decimal("3"),
            bom_level=1,
            is_top_level=True,
            is_self_made=False,
            sync_time=datetime(2026, 3, 18, 12, 0, 0),
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()

    resp = await app_client.get(
        "/api/data/bom-relations/tree",
        params={"machine_material_no": "MACH001,MACH003"},
    )
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["total"] == 2
    assert body["data"]["root_count"] == 2
    assert body["data"]["machine_material_nos"] == ["MACH001", "MACH003"]
    roots = body["data"]["roots"]
    assert [item["material_no"] for item in roots] == ["MACH001", "MACH003"]


@pytest.mark.asyncio
async def test_get_bom_tree_children(app_client, db_session):
    rows = [
        BomRelationSrc(
            machine_material_no="MACH001",
            machine_material_desc="整机A",
            plant="1000",
            material_no="MACH001",
            material_desc="整机A",
            bom_component_no="ASM001",
            bom_component_desc="机身体总成",
            part_type="自产件",
            component_qty=Decimal("1"),
            bom_level=1,
            is_top_level=True,
            is_self_made=True,
            sync_time=datetime(2026, 3, 18, 10, 0, 0),
        ),
        BomRelationSrc(
            machine_material_no="MACH001",
            machine_material_desc="整机A",
            plant="1000",
            material_no="ASM001",
            material_desc="机身体总成",
            bom_component_no="PART001",
            bom_component_desc="机身体焊接件",
            part_type="自产件",
            component_qty=Decimal("1"),
            bom_level=2,
            is_top_level=False,
            is_self_made=True,
            sync_time=datetime(2026, 3, 18, 10, 0, 0),
        ),
        BomRelationSrc(
            machine_material_no="MACH001",
            machine_material_desc="整机A",
            plant="1000",
            material_no="PART001",
            material_desc="机身体焊接件",
            bom_component_no="SUB001",
            bom_component_desc="焊接子件",
            part_type="自产件",
            component_qty=Decimal("1"),
            bom_level=3,
            is_top_level=False,
            is_self_made=True,
            sync_time=datetime(2026, 3, 18, 10, 0, 0),
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()

    resp = await app_client.get(
        "/api/data/bom-relations/tree/children",
        params={"machine_material_no": "MACH001", "parent_material_no": "ASM001"},
    )
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["machine_material_no"] == "MACH001"
    assert body["data"]["parent_material_no"] == "ASM001"
    assert body["data"]["total"] == 1
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["material_no"] == "PART001"
    assert body["data"]["items"][0]["has_children"] is True
    assert body["data"]["items"][0]["children_loaded"] is False
    assert body["data"]["items"][0]["children"] == []



@pytest.mark.asyncio
async def test_get_bom_tree_children_with_pagination(app_client, db_session):
    rows = [
        BomRelationSrc(
            machine_material_no="MACH001",
            machine_material_desc="Machine A",
            plant="1000",
            material_no="MACH001",
            material_desc="Machine A",
            bom_component_no="ASM001",
            bom_component_desc="Assembly 1",
            part_type="SELF_MADE",
            component_qty=Decimal("1"),
            bom_level=1,
            is_top_level=True,
            is_self_made=True,
            sync_time=datetime(2026, 3, 18, 10, 0, 0),
        ),
        BomRelationSrc(
            machine_material_no="MACH001",
            machine_material_desc="Machine A",
            plant="1000",
            material_no="MACH001",
            material_desc="Machine A",
            bom_component_no="ASM002",
            bom_component_desc="Assembly 2",
            part_type="SELF_MADE",
            component_qty=Decimal("1"),
            bom_level=1,
            is_top_level=True,
            is_self_made=True,
            sync_time=datetime(2026, 3, 18, 10, 0, 0),
        ),
        BomRelationSrc(
            machine_material_no="MACH001",
            machine_material_desc="Machine A",
            plant="1000",
            material_no="MACH001",
            material_desc="Machine A",
            bom_component_no="ASM003",
            bom_component_desc="Assembly 3",
            part_type="SELF_MADE",
            component_qty=Decimal("1"),
            bom_level=1,
            is_top_level=True,
            is_self_made=True,
            sync_time=datetime(2026, 3, 18, 10, 0, 0),
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()

    resp = await app_client.get(
        "/api/data/bom-relations/tree/children",
        params={
            "machine_material_no": "MACH001",
            "parent_material_no": "MACH001",
            "offset": 1,
            "limit": 1,
        },
    )
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["total"] == 3
    assert body["data"]["count"] == 1
    assert body["data"]["offset"] == 1
    assert body["data"]["limit"] == 1
    assert body["data"]["has_more"] is True
    assert body["data"]["next_offset"] == 2
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["material_no"] == "ASM002"


@pytest.mark.asyncio
async def test_list_bom_relations_filter_by_frontend_params(app_client, db_session):
    rows = [
        BomRelationSrc(
            machine_material_no="MACH-100",
            machine_material_desc="Machine 100",
            plant="1000",
            material_no="ASSY-100",
            material_desc="Assembly 100",
            bom_component_no="PART-SELF-100",
            bom_component_desc="Self Made Part",
            part_type="SELF_MADE",
            component_qty=Decimal("1"),
            bom_level=2,
            is_top_level=False,
            is_self_made=True,
            sync_time=datetime(2026, 3, 18, 10, 0, 0),
        ),
        BomRelationSrc(
            machine_material_no="MACH-200",
            machine_material_desc="Machine 200",
            plant="1000",
            material_no="ASSY-200",
            material_desc="Assembly 200",
            bom_component_no="PART-BUY-200",
            bom_component_desc="Purchased Part",
            part_type="PURCHASED",
            component_qty=Decimal("2"),
            bom_level=2,
            is_top_level=False,
            is_self_made=False,
            sync_time=datetime(2026, 3, 18, 11, 0, 0),
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()

    resp = await app_client.get("/api/data/bom-relations?machine_material_no=100")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["machine_material_no"] == "MACH-100"

    resp = await app_client.get("/api/data/bom-relations?material_no=ASSY-100")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["material_no"] == "ASSY-100"

    resp = await app_client.get("/api/data/bom-relations?bom_component_no=SELF-100")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["bom_component_no"] == "PART-SELF-100"

    resp = await app_client.get("/api/data/bom-relations?part_type=SELF")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["part_type"] == "SELF_MADE"
