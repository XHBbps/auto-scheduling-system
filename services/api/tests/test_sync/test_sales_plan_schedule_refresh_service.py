
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.assembly_time import AssemblyTimeBaseline
from app.models.bom_relation import BomRelationSrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.scheduler.schedule_orchestrator import ScheduleOrchestrator
from app.sync.sales_plan_schedule_refresh_service import SalesPlanScheduleRefreshService


@pytest.mark.asyncio
async def test_refresh_if_scheduled_marks_snapshot_stale_instead_of_deleting_results(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP900",
        sap_line_no="10",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACH900",
        quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 21),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
        order_no="SO900",
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80",
        product_series="MC1",
        order_qty=Decimal("1"),
        cycle_days_median=Decimal("1"),
        sample_count=5,
        is_active=True,
    ))
    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80",
        assembly_name="整机总装",
        assembly_time_days=Decimal("3"),
        is_final_assembly=True,
        production_sequence=99,
    ))
    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80",
        assembly_name="机身",
        assembly_time_days=Decimal("2"),
        is_final_assembly=False,
        production_sequence=1,
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH900",
        plant="1000",
        material_no="MACH900",
        bom_component_no="ASM900",
        bom_component_desc="机身总成MC1-80",
        bom_level=1,
        is_self_made=True,
        part_type="自产件",
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH900",
        plant="1000",
        material_no="ASM900",
        bom_component_no="PART900",
        bom_component_desc="机身焊接件",
        bom_level=2,
        is_self_made=True,
        part_type="自产件",
    ))
    await db_session.commit()

    first_result = await ScheduleOrchestrator(db_session).schedule_order(order.id)
    await db_session.commit()
    assert first_result["success"] is True

    order.confirmed_delivery_date = datetime(2026, 3, 20)
    await db_session.flush()

    refresh_result = await SalesPlanScheduleRefreshService(db_session).refresh_if_scheduled(
        order_line_id=order.id,
        changed_fields=["confirmed_delivery_date"],
    )
    await db_session.commit()

    machine_results = (
        await db_session.execute(
            select(MachineScheduleResult).where(MachineScheduleResult.order_line_id == order.id)
        )
    ).scalars().all()
    snapshot = (
        await db_session.execute(
            select(OrderScheduleSnapshot).where(OrderScheduleSnapshot.order_line_id == order.id)
        )
    ).scalar_one()

    assert refresh_result["triggered"] is True
    assert refresh_result["stale_marked"] is True
    assert len(machine_results) == 1
    assert snapshot.schedule_status == "scheduled_stale"
    assert snapshot.status_reason == "sales_plan_changed:confirmed_delivery_date"
