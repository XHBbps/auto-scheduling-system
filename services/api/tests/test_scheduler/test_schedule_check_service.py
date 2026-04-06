from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.bom_relation import BomRelationSrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.scheduler.schedule_check_service import ScheduleCheckService


def _machine_bom(material_no: str) -> BomRelationSrc:
    return BomRelationSrc(
        machine_material_no=material_no,
        plant="1000",
        material_no=material_no,
        bom_component_no=f"ASM-{material_no}",
        bom_component_desc="机身总成",
        bom_level=1,
        is_self_made=True,
        part_type="自产件",
    )


@pytest.mark.asyncio
async def test_pending_drawing(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001",
        sap_line_no="10",
        confirmed_delivery_date=datetime(2026, 9, 1),
        drawing_released=False,
        product_model="MC1-80",
        quantity=Decimal("1"),
        material_no="MACH-001",
    )
    db_session.add(order)
    await db_session.commit()

    result = await ScheduleCheckService(db_session).check(order.id)
    assert result["status"] == "pending_drawing"
    assert result["is_schedulable"] is False
    assert result["resource_snapshot"]["inventory"]["status"] == "not_integrated"
    assert result["resource_snapshot"]["capacity"]["status"] == "not_integrated"


@pytest.mark.asyncio
async def test_pending_trigger(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP002",
        sap_line_no="10",
        confirmed_delivery_date=datetime(2026, 12, 1),
        drawing_released=True,
        product_model="MC1-80",
        quantity=Decimal("1"),
        material_no="MACH-002",
    )
    db_session.add(order)
    db_session.add(_machine_bom("MACH-002"))
    db_session.add(
        MachineCycleBaseline(
            machine_model="MC1-80",
            product_series="MC1",
            order_qty=Decimal("1"),
            cycle_days_median=Decimal("90"),
            sample_count=5,
            is_active=True,
        )
    )
    await db_session.commit()

    result = await ScheduleCheckService(db_session, today=date(2026, 3, 17)).check(order.id)
    assert result["status"] == "pending_trigger"
    assert result["trigger_date"] is not None


@pytest.mark.asyncio
async def test_schedulable(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP003",
        sap_line_no="10",
        confirmed_delivery_date=datetime(2026, 6, 1),
        drawing_released=True,
        product_model="MC1-80",
        quantity=Decimal("1"),
        material_no="MACH-003",
    )
    db_session.add(order)
    db_session.add(_machine_bom("MACH-003"))
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
    await db_session.commit()

    result = await ScheduleCheckService(db_session, today=date(2026, 3, 17)).check(order.id)
    assert result["status"] == "schedulable"
    assert result["is_schedulable"] is True
    assert result["resource_snapshot"]["inventory"]["material_no"] == "MACH-003"
    assert result["resource_snapshot"]["capacity"]["product_model"] == "MC1-80"
    assert result["resource_snapshot"]["capacity"]["trigger_date"] is not None


@pytest.mark.asyncio
async def test_no_delivery_date(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP004",
        sap_line_no="10",
        confirmed_delivery_date=None,
        drawing_released=True,
        product_model="MC1-80",
        quantity=Decimal("1"),
        material_no="MACH-004",
    )
    db_session.add(order)
    await db_session.commit()

    result = await ScheduleCheckService(db_session).check(order.id)
    assert result["is_schedulable"] is False
    assert result["status"] == "pending_delivery"


@pytest.mark.asyncio
async def test_duplicate_active_baselines_do_not_break_exact_match(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP005",
        sap_line_no="10",
        confirmed_delivery_date=datetime(2026, 6, 1),
        drawing_released=True,
        product_model="MC2-200",
        quantity=Decimal("1"),
        material_no="MACH-005",
    )
    db_session.add(order)
    db_session.add(_machine_bom("MACH-005"))
    db_session.add_all(
        [
            MachineCycleBaseline(
                machine_model="MC2-200",
                product_series="old",
                order_qty=Decimal("1"),
                cycle_days_median=Decimal("60"),
                sample_count=1,
                is_active=True,
            ),
            MachineCycleBaseline(
                machine_model="MC2-200",
                product_series="new",
                order_qty=Decimal("1"),
                cycle_days_median=Decimal("51"),
                sample_count=18,
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    result = await ScheduleCheckService(db_session, today=date(2026, 3, 17)).check(order.id)
    assert result["status"] == "pending_trigger"
    assert result["is_schedulable"] is False
    assert result["machine_cycle_days"] == Decimal("51")
