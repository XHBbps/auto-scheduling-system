from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models.assembly_time import AssemblyTimeBaseline
from app.models.bom_relation import BomRelationSrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.bom_relation_repo import BomRelationRepo
from app.scheduler.schedule_orchestrator import ScheduleOrchestrator
from app.sync.bom_sync_service import BomSyncService


@pytest.mark.asyncio
async def test_sync_bom_delete_insert(db_session):
    # Pre-insert old BOM data
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH001",
            plant="1000",
            bom_component_no="OLD_COMP",
            bom_level=1,
        )
    )
    await db_session.commit()

    mock_client = AsyncMock()
    mock_client.fetch_bom.return_value = [
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "压力机",
            "material_no": "MACH001",
            "material_desc": "压力机",
            "plant": "1000",
            "bom_component_no": "COMP001",
            "bom_component_desc": "机身MC1-80",
            "part_type": "自产件",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "压力机",
            "material_no": "MACH001",
            "material_desc": "压力机",
            "plant": "1000",
            "bom_component_no": "COMP002",
            "bom_component_desc": "电气柜",
            "part_type": "外购件",
            "component_qty": Decimal("2"),
            "is_self_made": False,
        },
    ]

    service = BomSyncService(db_session, mock_client)
    result = await service.sync_for_order(machine_material_no="MACH001", plant="1000")
    await db_session.commit()

    repo = BomRelationRepo(db_session)
    rows = await repo.find_by_machine("MACH001")
    # Old data should be deleted, 2 new rows inserted
    assert len(rows) == 2
    assert result.success_count == 2


@pytest.mark.asyncio
async def test_bom_level_assignment(db_session):
    mock_client = AsyncMock()
    # Simulate a 2-level BOM: MACH001 -> COMP001 -> SUBCOMP001
    mock_client.fetch_bom.return_value = [
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "压力机",
            "material_no": "MACH001",
            "material_desc": "压力机",
            "plant": "1000",
            "bom_component_no": "COMP001",
            "bom_component_desc": "机身",
            "part_type": "自产件",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "压力机",
            "material_no": "COMP001",
            "material_desc": "机身",
            "plant": "1000",
            "bom_component_no": "SUBCOMP001",
            "bom_component_desc": "铸件",
            "part_type": "自产件",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
    ]

    service = BomSyncService(db_session, mock_client)
    await service.sync_for_order(machine_material_no="MACH001", plant="1000")
    await db_session.commit()

    repo = BomRelationRepo(db_session)
    rows = await repo.find_by_machine("MACH001")
    level_map = {r.bom_component_no: r.bom_level for r in rows}
    assert level_map["COMP001"] == 1  # direct child of machine
    assert level_map["SUBCOMP001"] == 2  # child of COMP001


@pytest.mark.asyncio
async def test_bom_level_assignment_uses_parent_path_not_shared_component_no(db_session):
    mock_client = AsyncMock()
    mock_client.fetch_bom.return_value = [
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "Pressure Machine",
            "material_no": "MACH001",
            "material_desc": "Pressure Machine",
            "plant": "1000",
            "bom_component_no": "ASM-SHALLOW",
            "bom_component_desc": "Shallow Assembly",
            "part_type": "SELF_MADE",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "Pressure Machine",
            "material_no": "ASM-SHALLOW",
            "material_desc": "Shallow Assembly",
            "plant": "1000",
            "bom_component_no": "COMP-SHARED",
            "bom_component_desc": "Shared Component",
            "part_type": "SELF_MADE",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "Pressure Machine",
            "material_no": "MACH001",
            "material_desc": "Pressure Machine",
            "plant": "1000",
            "bom_component_no": "ASM-DEEP",
            "bom_component_desc": "Deep Assembly",
            "part_type": "SELF_MADE",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "Pressure Machine",
            "material_no": "ASM-DEEP",
            "material_desc": "Deep Assembly",
            "plant": "1000",
            "bom_component_no": "MID-001",
            "bom_component_desc": "Middle Assembly",
            "part_type": "SELF_MADE",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "Pressure Machine",
            "material_no": "MID-001",
            "material_desc": "Middle Assembly",
            "plant": "1000",
            "bom_component_no": "COMP-SHARED",
            "bom_component_desc": "Shared Component",
            "part_type": "SELF_MADE",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
    ]

    service = BomSyncService(db_session, mock_client)
    await service.sync_for_order(machine_material_no="MACH001", plant="1000")
    await db_session.commit()

    repo = BomRelationRepo(db_session)
    rows = await repo.find_by_machine("MACH001")
    level_map = {(r.material_no, r.bom_component_no): r.bom_level for r in rows}

    assert level_map[("ASM-SHALLOW", "COMP-SHARED")] == 2
    assert level_map[("MID-001", "COMP-SHARED")] == 3


@pytest.mark.asyncio
async def test_sync_bom_keeps_existing_scheduled_snapshot_scheduled(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP-BOM-1",
        sap_line_no="10",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACH-BOM-1",
        quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 21),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)
    db_session.add(
        MachineCycleBaseline(
            machine_model="MC1-80",
            product_series="MC1",
            order_qty=Decimal("1"),
            cycle_days_median=Decimal("1"),
            sample_count=5,
            is_active=True,
        )
    )
    db_session.add(
        AssemblyTimeBaseline(
            machine_model="MC1-80",
            assembly_name="整机总装",
            assembly_time_days=Decimal("3"),
            is_final_assembly=True,
            production_sequence=99,
        )
    )
    db_session.add(
        AssemblyTimeBaseline(
            machine_model="MC1-80",
            assembly_name="机身",
            assembly_time_days=Decimal("2"),
            is_final_assembly=False,
            production_sequence=1,
        )
    )
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH-BOM-1",
            plant="1000",
            material_no="MACH-BOM-1",
            bom_component_no="ASM-BOM-1",
            bom_component_desc="机身",
            bom_level=1,
            is_self_made=True,
            part_type="自制件",
        )
    )
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH-BOM-1",
            plant="1000",
            material_no="ASM-BOM-1",
            bom_component_no="PART-BOM-1",
            bom_component_desc="传动轴",
            bom_level=2,
            is_self_made=True,
            part_type="自制件",
        )
    )
    await db_session.commit()

    result = await ScheduleOrchestrator(db_session).schedule_order(order.id)
    await db_session.commit()
    assert result["success"] is True

    mock_client = AsyncMock()
    mock_client.fetch_bom.return_value = [
        {
            "machine_material_no": "MACH-BOM-1",
            "machine_material_desc": "压力机",
            "material_no": "MACH-BOM-1",
            "material_desc": "压力机",
            "plant": "1000",
            "bom_component_no": "ASM-BOM-1",
            "bom_component_desc": "机身",
            "part_type": "自制件",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
        {
            "machine_material_no": "MACH-BOM-1",
            "machine_material_desc": "压力机",
            "material_no": "ASM-BOM-1",
            "material_desc": "机身",
            "plant": "1000",
            "bom_component_no": "PART-BOM-1",
            "bom_component_desc": "传动轴",
            "part_type": "自制件",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
    ]

    service = BomSyncService(db_session, mock_client)
    sync_result = await service.sync_for_order(machine_material_no="MACH-BOM-1", plant="1000")
    await db_session.commit()

    snapshot = (
        await db_session.execute(select(OrderScheduleSnapshot).where(OrderScheduleSnapshot.order_line_id == order.id))
    ).scalar_one()

    assert sync_result.fail_count == 0
    assert snapshot.schedule_status == "scheduled"
