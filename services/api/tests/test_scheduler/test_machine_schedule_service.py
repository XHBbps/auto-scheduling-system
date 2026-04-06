from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.assembly_time import AssemblyTimeBaseline
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.scheduler.machine_schedule_service import MachineScheduleService


@pytest.mark.asyncio
async def test_build_machine_schedule(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001",
        sap_line_no="10",
        contract_no="HT001",
        customer_name="客户A",
        product_series="MC1",
        product_model="MC1-80",
        product_name="压力机",
        material_no="MACH001",
        quantity=Decimal("1"),
        order_no="SO001",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)
    db_session.add(
        MachineCycleBaseline(
            machine_model="MC1-80",
            product_series="MC1",
            order_qty=Decimal("1"),
            cycle_days_median=Decimal("60"),
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
    await db_session.commit()

    service = MachineScheduleService(db_session, today=date(2026, 3, 17))
    result = await service.build(order.id)
    await db_session.commit()

    assert result is not None
    assert result.planned_end_date.date() == date(2026, 6, 30)
    assert result.machine_cycle_days == Decimal("60")
    assert result.machine_assembly_days == Decimal("3")
    assert result.trigger_date == result.planned_start_date
    assert result.planned_start_date is not None
    assert result.schedule_status == "scheduled"


@pytest.mark.asyncio
async def test_default_final_assembly(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP002",
        sap_line_no="10",
        product_model="MC2-100",
        quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
    )
    db_session.add(order)
    await db_session.commit()

    service = MachineScheduleService(db_session, today=date(2026, 3, 17))
    result = await service.build(order.id)
    await db_session.commit()

    assert result is not None
    assert result.machine_assembly_days == Decimal("3")
