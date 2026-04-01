import pytest
from decimal import Decimal
from datetime import datetime

from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.bom_relation import BomRelationSrc
from app.models.part_cycle_baseline import PartCycleBaseline
from app.models.assembly_time import AssemblyTimeBaseline
from app.models.machine_schedule_result import MachineScheduleResult
from app.scheduler.part_schedule_service import PartScheduleService


@pytest.mark.asyncio
async def test_build_part_schedules(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH001", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
    )
    db_session.add(order)
    await db_session.flush()

    msr = MachineScheduleResult(
        order_line_id=order.id,
        product_model="MC1-80",
        planned_start_date=datetime(2026, 4, 1),
        planned_end_date=datetime(2026, 6, 30),
        machine_cycle_days=Decimal("60"),
        machine_assembly_days=Decimal("3"),
    )
    db_session.add(msr)

    db_session.add(BomRelationSrc(
        machine_material_no="MACH001", plant="1000",
        material_no="MACH001", bom_component_no="ASM_BODY",
        bom_component_desc="机身MC1-80", bom_level=1,
        is_top_level=True,
        is_self_made=True, part_type="自产件",
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH001", plant="1000",
        material_no="ASM_BODY", bom_component_no="PART_CAST",
        bom_component_desc="铸件机身", bom_level=2,
        is_self_made=True, part_type="自产件",
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH001", plant="1000",
        material_no="ASM_BODY", bom_component_no="PART_PLATE",
        bom_component_desc="机身板件", bom_level=2,
        is_self_made=True, part_type="自产件",
    ))

    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80", assembly_name="机身",
        assembly_time_days=Decimal("2"), production_sequence=1,
        is_final_assembly=False,
    ))

    db_session.add(PartCycleBaseline(
        material_no="PART_CAST", material_desc="铸件机身",
        core_part_name="铸件", machine_model="MC1-80",
        ref_batch_qty=Decimal("1"), cycle_days=Decimal("15"),
        unit_cycle_days=Decimal("15"), is_active=True,
    ))
    db_session.add(PartCycleBaseline(
        material_no="PART_PLATE", material_desc="机身板件",
        core_part_name="板件", machine_model="MC1-80",
        ref_batch_qty=Decimal("1"), cycle_days=Decimal("5"),
        unit_cycle_days=Decimal("5"), is_active=True,
    ))
    await db_session.commit()

    service = PartScheduleService(db_session)
    parts = await service.build(order.id, msr.id)
    await db_session.commit()

    body_parts = [p for p in parts if p.assembly_name == "机身"]
    assert len(body_parts) == 2

    key_part = [p for p in body_parts if p.is_key_part][0]
    non_key_part = [p for p in body_parts if not p.is_key_part][0]

    assert key_part.part_material_no == "PART_CAST"
    assert key_part.part_cycle_days == Decimal("15")
    assert key_part.part_cycle_is_default is False
    assert key_part.key_part_material_no == "PART_CAST"
    assert key_part.key_part_cycle_days == Decimal("15")
    assert key_part.planned_end_date is not None
    assert key_part.planned_start_date is not None
    assert key_part.planned_end_date < msr.planned_end_date
    assert key_part.parent_material_no == "ASM_BODY"
    assert key_part.parent_name == "机身"
    assert key_part.node_level == 1
    assert key_part.bom_path == "机身(ASM_BODY) / 铸件机身(PART_CAST)"
    assert key_part.bom_path_key is not None

    assert non_key_part.part_material_no == "PART_PLATE"
    assert non_key_part.part_cycle_days == Decimal("5")
    assert non_key_part.part_cycle_is_default is False
    assert non_key_part.key_part_material_no == "PART_CAST"
    assert non_key_part.planned_start_date == key_part.planned_start_date


@pytest.mark.asyncio
async def test_build_part_schedules_uses_prefetched_children_and_key_part(monkeypatch, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP002", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH002", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
    )
    db_session.add(order)
    await db_session.flush()

    msr = MachineScheduleResult(
        order_line_id=order.id,
        product_model="MC1-80",
        planned_start_date=datetime(2026, 4, 1),
        planned_end_date=datetime(2026, 6, 30),
        machine_cycle_days=Decimal("60"),
        machine_assembly_days=Decimal("3"),
    )
    db_session.add(msr)

    db_session.add(BomRelationSrc(
        machine_material_no="MACH002", plant="1000",
        material_no="MACH002", bom_component_no="ASM_BODY",
        bom_component_desc="机身MC1-80", bom_level=1,
        is_top_level=True, is_self_made=True, part_type="自制件",
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH002", plant="1000",
        material_no="ASM_BODY", bom_component_no="PART_CAST",
        bom_component_desc="铸件机身", bom_level=2,
        is_self_made=True, part_type="自制件",
    ))
    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80", assembly_name="机身",
        assembly_time_days=Decimal("2"), production_sequence=1,
        is_final_assembly=False,
    ))
    db_session.add(PartCycleBaseline(
        material_no="PART_CAST", material_desc="铸件机身",
        core_part_name="铸件", machine_model="MC1-80",
        ref_batch_qty=Decimal("1"), cycle_days=Decimal("15"),
        unit_cycle_days=Decimal("15"), is_active=True,
    ))
    await db_session.commit()

    service = PartScheduleService(db_session)

    async def fail_list_self_made_parts(*args, **kwargs):
        raise AssertionError("build() should not call per-assembly list_self_made_parts")

    async def fail_identify(*args, **kwargs):
        raise AssertionError("build() should not call identify() that refetches children")

    monkeypatch.setattr(service.key_part_service, "list_self_made_parts", fail_list_self_made_parts)
    monkeypatch.setattr(service.key_part_service, "identify", fail_identify)

    parts = await service.build(order.id, msr.id)

    assert len(parts) == 1
    assert parts[0].part_material_no == "PART_CAST"
    assert parts[0].is_key_part is True


@pytest.mark.asyncio
async def test_build_part_schedules_recursively_collects_all_self_made_nodes(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP003", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH003", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
    )
    db_session.add(order)
    await db_session.flush()

    msr = MachineScheduleResult(
        order_line_id=order.id,
        product_model="MC1-80",
        planned_start_date=datetime(2026, 4, 1),
        planned_end_date=datetime(2026, 6, 30),
        machine_cycle_days=Decimal("60"),
        machine_assembly_days=Decimal("3"),
    )
    db_session.add(msr)

    db_session.add_all([
        BomRelationSrc(
            machine_material_no="MACH003", plant="1000",
            material_no="MACH003", bom_component_no="ASM_BODY",
            bom_component_desc="机身MC1-80", bom_level=1,
            is_top_level=True, is_self_made=True, part_type="自制件",
        ),
        BomRelationSrc(
            machine_material_no="MACH003", plant="1000",
            material_no="ASM_BODY", bom_component_no="SUB_LEFT",
            bom_component_desc="左子总成", bom_level=2,
            is_self_made=True, part_type="自制件",
        ),
        BomRelationSrc(
            machine_material_no="MACH003", plant="1000",
            material_no="ASM_BODY", bom_component_no="SUB_RIGHT",
            bom_component_desc="右子总成", bom_level=2,
            is_self_made=True, part_type="自制件",
        ),
        BomRelationSrc(
            machine_material_no="MACH003", plant="1000",
            material_no="SUB_LEFT", bom_component_no="PART_SHARED",
            bom_component_desc="共享件", bom_level=3,
            is_self_made=True, part_type="自制件",
        ),
        BomRelationSrc(
            machine_material_no="MACH003", plant="1000",
            material_no="SUB_RIGHT", bom_component_no="PART_SHARED",
            bom_component_desc="共享件", bom_level=3,
            is_self_made=True, part_type="自制件",
        ),
    ])
    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80", assembly_name="机身",
        assembly_time_days=Decimal("2"), production_sequence=1,
        is_final_assembly=False,
    ))
    db_session.add(PartCycleBaseline(
        material_no="PART_SHARED", material_desc="共享件",
        core_part_name="共享件", machine_model="MC1-80",
        ref_batch_qty=Decimal("1"), cycle_days=Decimal("12"),
        unit_cycle_days=Decimal("12"), is_active=True,
    ))
    await db_session.commit()

    service = PartScheduleService(db_session)
    parts = await service.build(order.id, msr.id)

    body_parts = [p for p in parts if p.assembly_name == "机身"]
    assert len(body_parts) == 4

    sub_assemblies = [p for p in body_parts if p.part_material_no in {"SUB_LEFT", "SUB_RIGHT"}]
    shared_parts = [p for p in body_parts if p.part_material_no == "PART_SHARED"]
    assert len(sub_assemblies) == 2
    assert len(shared_parts) == 2
    assert {item.node_level for item in sub_assemblies} == {1}
    assert {item.node_level for item in shared_parts} == {2}
    assert all(item.parent_material_no in {"ASM_BODY", "SUB_LEFT", "SUB_RIGHT"} for item in body_parts)
    assert len({item.bom_path_key for item in shared_parts}) == 2
    assert len({item.bom_path for item in shared_parts}) == 2
    assert sum(1 for item in body_parts if item.is_key_part) == 1
    assert all(item.key_part_material_no == "PART_SHARED" for item in body_parts)
    assert all(item.planned_start_date == body_parts[0].planned_start_date for item in body_parts)
    assert all(item.planned_end_date == body_parts[0].planned_end_date for item in body_parts)


@pytest.mark.asyncio
async def test_build_part_schedules_rejects_mismatched_machine_schedule_binding(db_session):
    order_a = SalesPlanOrderLineSrc(
        sap_code="SAP004", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH004", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
    )
    order_b = SalesPlanOrderLineSrc(
        sap_code="SAP005", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH005", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
    )
    db_session.add_all([order_a, order_b])
    await db_session.flush()

    msr = MachineScheduleResult(
        order_line_id=order_b.id,
        product_model="MC1-80",
        planned_start_date=datetime(2026, 4, 1),
        planned_end_date=datetime(2026, 6, 30),
        machine_cycle_days=Decimal("60"),
        machine_assembly_days=Decimal("3"),
    )
    db_session.add(msr)
    await db_session.commit()

    service = PartScheduleService(db_session)

    with pytest.raises(ValueError, match="does not belong"):
        await service.build(order_a.id, msr.id)
