from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.assembly_time import AssemblyTimeBaseline
from app.models.bom_relation import BomRelationSrc
from app.models.data_issue import DataIssueRecord
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.part_cycle_baseline import PartCycleBaseline
from app.models.part_schedule_result import PartScheduleResult
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.scheduler.schedule_orchestrator import ScheduleOrchestrator


@pytest.mark.asyncio
async def test_full_schedule_single_order(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001",
        sap_line_no="10",
        contract_no="HT001",
        customer_name="客户A",
        product_model="MC1-80",
        product_series="MC1",
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
        BomRelationSrc(
            machine_material_no="MACH001",
            plant="1000",
            material_no="MACH001",
            bom_component_no="ASM_BODY",
            bom_component_desc="机身MC1-80",
            bom_level=2,
            is_self_made=True,
            part_type="自产件",
        )
    )
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH001",
            plant="1000",
            material_no="ASM_BODY",
            bom_component_no="PART_CAST",
            bom_component_desc="铸件机身",
            bom_level=3,
            is_self_made=True,
            part_type="自产件",
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
        PartCycleBaseline(
            material_no="PART_CAST",
            material_desc="铸件机身",
            core_part_name="铸件",
            machine_model="MC1-80",
            ref_batch_qty=Decimal("1"),
            cycle_days=Decimal("15"),
            unit_cycle_days=Decimal("15"),
            is_active=True,
        )
    )
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 5, 1))
    result = await orchestrator.schedule_order(order.id)
    await db_session.commit()

    assert result["success"] is True
    assert result["machine_schedule"] is not None
    assert len(result["part_schedules"]) >= 1


@pytest.mark.asyncio
async def test_skip_not_schedulable(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP002",
        sap_line_no="10",
        product_model="MC1-80",
        confirmed_delivery_date=None,
        drawing_released=False,
    )
    db_session.add(order)
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 3, 17))
    result = await orchestrator.schedule_order(order.id)

    assert result["success"] is False
    assert result["reason"] is not None


@pytest.mark.asyncio
async def test_batch_schedule(db_session):
    orders = []
    for i in range(3):
        o = SalesPlanOrderLineSrc(
            sap_code=f"SAP00{i}",
            sap_line_no="10",
            product_model="MC1-80",
            quantity=Decimal("1"),
            material_no="MACH001",
            confirmed_delivery_date=datetime(2026, 6, 30),
            drawing_released=True,
        )
        db_session.add(o)
        orders.append(o)
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 3, 17))
    batch_result = await orchestrator.schedule_batch([o.id for o in orders])
    await db_session.commit()

    assert batch_result["total"] == 3
    assert batch_result["scheduled"] + batch_result["failed"] == 3


@pytest.mark.asyncio
async def test_missing_bom_blocks_schedule_and_records_issue(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP999",
        sap_line_no="10",
        contract_no="HT999",
        customer_name="客户B",
        product_model="MC2-45",
        product_series="MC2",
        material_no="MACH999",
        quantity=Decimal("1"),
        order_no="SO999",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
    )
    db_session.add(order)
    db_session.add(
        MachineCycleBaseline(
            machine_model="MC2-45",
            product_series="MC2",
            order_qty=Decimal("1"),
            cycle_days_median=Decimal("45"),
            sample_count=5,
            is_active=True,
        )
    )
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 5, 1))
    result = await orchestrator.schedule_order(order.id)
    await db_session.commit()

    assert result["success"] is False
    assert result["status"] == "missing_bom"

    issues = (
        (await db_session.execute(select(DataIssueRecord).where(DataIssueRecord.biz_key == str(order.id))))
        .scalars()
        .all()
    )
    assert len(issues) == 1
    assert issues[0].issue_type == "BOM缺失"
    assert issues[0].issue_title == "排产前缺少 BOM 数据"


@pytest.mark.asyncio
async def test_missing_machine_cycle_records_issue_and_marks_abnormal(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP888",
        sap_line_no="10",
        contract_no="HT888",
        customer_name="客户C",
        product_model="PSP-80B(二级传动)",
        product_series="PSP",
        material_no="MACH888",
        quantity=Decimal("1"),
        order_no="SO888",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
    )
    db_session.add(order)
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH888",
            plant="1000",
            material_no="MACH888",
            bom_component_no="ASM_X",
            bom_component_desc="机身PSP-80B",
            bom_level=2,
            is_self_made=True,
            part_type="自产件",
        )
    )
    db_session.add(
        AssemblyTimeBaseline(
            machine_model="PSP-80B(二级传动)",
            assembly_name="整机总装",
            assembly_time_days=Decimal("3"),
            is_final_assembly=True,
            production_sequence=99,
        )
    )
    db_session.add(
        AssemblyTimeBaseline(
            machine_model="PSP-80B(二级传动)",
            assembly_name="机身",
            assembly_time_days=Decimal("2"),
            is_final_assembly=False,
            production_sequence=1,
        )
    )
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 5, 1))
    result = await orchestrator.schedule_order(order.id)
    await db_session.commit()

    assert result["success"] is True
    assert result["machine_schedule"].warning_level == "abnormal"
    assert result["machine_schedule"].issue_flags["machine_cycle_default"] is True

    issues = (
        (await db_session.execute(select(DataIssueRecord).where(DataIssueRecord.biz_key == str(order.id))))
        .scalars()
        .all()
    )
    assert len(issues) == 1
    assert issues[0].issue_type == "整机周期基准缺失"
    assert issues[0].issue_title == "整机周期基准缺失，已按默认值排产"


@pytest.mark.asyncio
async def test_pending_drawing_records_issue(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP777",
        sap_line_no="10",
        contract_no="HT777",
        customer_name="客户D",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACH777",
        quantity=Decimal("1"),
        order_no="SO777",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=False,
    )
    db_session.add(order)
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 5, 1))
    result = await orchestrator.schedule_order(order.id)
    await db_session.commit()

    issue = (
        (await db_session.execute(select(DataIssueRecord).where(DataIssueRecord.biz_key == str(order.id))))
        .scalars()
        .first()
    )

    assert result["success"] is False
    assert result["status"] == "pending_drawing"
    assert issue is not None
    assert issue.issue_type == "发图状态未完成"
    assert issue.issue_title == "排产前发图状态未完成"


@pytest.mark.asyncio
async def test_pending_delivery_records_issue(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP778",
        sap_line_no="10",
        contract_no="HT778",
        customer_name="客户E",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACH778",
        quantity=Decimal("1"),
        order_no="SO778",
        confirmed_delivery_date=None,
        drawing_released=True,
    )
    db_session.add(order)
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 5, 1))
    result = await orchestrator.schedule_order(order.id)
    await db_session.commit()

    issue = (
        (await db_session.execute(select(DataIssueRecord).where(DataIssueRecord.biz_key == str(order.id))))
        .scalars()
        .first()
    )

    assert result["success"] is False
    assert result["status"] == "pending_delivery"
    assert issue is not None
    assert issue.issue_type == "确认交货期缺失"
    assert issue.issue_title == "排产前缺少确认交货期"


@pytest.mark.asyncio
async def test_missing_part_cycle_records_issue_and_marks_abnormal(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP666",
        sap_line_no="10",
        contract_no="HT666",
        customer_name="客户E",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACH666",
        quantity=Decimal("1"),
        order_no="SO666",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
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
        BomRelationSrc(
            machine_material_no="MACH666",
            plant="1000",
            material_no="MACH666",
            bom_component_no="ASM666",
            bom_component_desc="机身MC1-80",
            bom_level=1,
            is_top_level=True,
            is_self_made=True,
            part_type="自产件",
        )
    )
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH666",
            plant="1000",
            material_no="ASM666",
            bom_component_no="PART666",
            bom_component_desc="机身焊接件",
            bom_level=2,
            is_self_made=True,
            part_type="自产件",
        )
    )
    db_session.add(
        AssemblyTimeBaseline(
            machine_model="MC1-80",
            assembly_name="机身",
            assembly_time_days=Decimal("2"),
            production_sequence=1,
            is_final_assembly=False,
        )
    )
    db_session.add(
        AssemblyTimeBaseline(
            machine_model="MC1-80",
            assembly_name="整机总装",
            assembly_time_days=Decimal("3"),
            production_sequence=99,
            is_final_assembly=True,
        )
    )
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 5, 1))
    result = await orchestrator.schedule_order(order.id)
    await db_session.commit()

    issue = (
        (
            await db_session.execute(
                select(DataIssueRecord).where(
                    DataIssueRecord.biz_key == str(order.id),
                    DataIssueRecord.issue_type == "零件周期基准缺失",
                )
            )
        )
        .scalars()
        .first()
    )

    assert result["success"] is True
    assert result["machine_schedule"].warning_level == "abnormal"
    assert result["machine_schedule"].issue_flags["part_schedule_default"] is True
    assert len(result["part_schedules"]) == 1
    assert result["part_schedules"][0].warning_level == "abnormal"
    assert result["part_schedules"][0].issue_flags["part_cycle_default"] is True
    assert result["part_schedules"][0].issue_flags["key_part_cycle_default"] is True
    assert issue is not None
    assert issue.issue_title == "零件周期基准缺失，已按默认值排产"


@pytest.mark.asyncio
async def test_missing_assembly_time_records_issue_and_marks_abnormal(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP555",
        sap_line_no="10",
        contract_no="HT555",
        customer_name="客户F",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACH555",
        quantity=Decimal("1"),
        order_no="SO555",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
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
        BomRelationSrc(
            machine_material_no="MACH555",
            plant="1000",
            material_no="MACH555",
            bom_component_no="ASM555",
            bom_component_desc="机身MC1-80",
            bom_level=1,
            is_top_level=True,
            is_self_made=True,
            part_type="自产件",
        )
    )
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH555",
            plant="1000",
            material_no="ASM555",
            bom_component_no="PART555",
            bom_component_desc="机身焊接件",
            bom_level=2,
            is_self_made=True,
            part_type="自产件",
        )
    )
    db_session.add(
        PartCycleBaseline(
            material_no="PART555",
            material_desc="机身焊接件",
            core_part_name="焊接件",
            machine_model="MC1-80",
            ref_batch_qty=Decimal("1"),
            cycle_days=Decimal("8"),
            unit_cycle_days=Decimal("8"),
            is_active=True,
        )
    )
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 5, 1))
    result = await orchestrator.schedule_order(order.id)
    await db_session.commit()

    issue = (
        (
            await db_session.execute(
                select(DataIssueRecord).where(
                    DataIssueRecord.biz_key == str(order.id),
                    DataIssueRecord.issue_type == "装配时长基准缺失",
                )
            )
        )
        .scalars()
        .first()
    )

    assert result["success"] is True
    assert result["machine_schedule"].warning_level == "abnormal"
    assert result["machine_schedule"].issue_flags["final_assembly_time_default"] is True
    assert len(result["part_schedules"]) == 1
    assert result["part_schedules"][0].warning_level == "abnormal"
    assert result["part_schedules"][0].issue_flags["assembly_time_default"] is True
    assert issue is not None
    assert issue.issue_title == "装配时长基准缺失，已按默认值排产"


@pytest.mark.asyncio
async def test_batch_schedule_rolls_back_partial_data_when_single_order_raises(db_session, monkeypatch):
    order_ok = SalesPlanOrderLineSrc(
        sap_code="SAPB001",
        sap_line_no="10",
        contract_no="HTB001",
        customer_name="客户G",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACHB001",
        quantity=Decimal("1"),
        order_no="SOB001",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
    )
    order_fail = SalesPlanOrderLineSrc(
        sap_code="SAPB002",
        sap_line_no="10",
        contract_no="HTB002",
        customer_name="客户H",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACHB002",
        quantity=Decimal("1"),
        order_no="SOB002",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
    )
    db_session.add_all([order_ok, order_fail])
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
    db_session.add_all(
        [
            BomRelationSrc(
                machine_material_no="MACHB001",
                plant="1000",
                material_no="MACHB001",
                bom_component_no="ASM_B001",
                bom_component_desc="机身MC1-80",
                bom_level=1,
                is_top_level=True,
                is_self_made=True,
                part_type="自产件",
            ),
            BomRelationSrc(
                machine_material_no="MACHB001",
                plant="1000",
                material_no="ASM_B001",
                bom_component_no="PART_B001",
                bom_component_desc="机身焊接件",
                bom_level=2,
                is_self_made=True,
                part_type="自产件",
            ),
            BomRelationSrc(
                machine_material_no="MACHB002",
                plant="1000",
                material_no="MACHB002",
                bom_component_no="ASM_B002",
                bom_component_desc="机身MC1-80",
                bom_level=1,
                is_top_level=True,
                is_self_made=True,
                part_type="自产件",
            ),
            BomRelationSrc(
                machine_material_no="MACHB002",
                plant="1000",
                material_no="ASM_B002",
                bom_component_no="PART_B002",
                bom_component_desc="机身焊接件",
                bom_level=2,
                is_self_made=True,
                part_type="自产件",
            ),
        ]
    )
    db_session.add_all(
        [
            AssemblyTimeBaseline(
                machine_model="MC1-80",
                assembly_name="机身",
                assembly_time_days=Decimal("2"),
                production_sequence=1,
                is_final_assembly=False,
            ),
            AssemblyTimeBaseline(
                machine_model="MC1-80",
                assembly_name="整机总装",
                assembly_time_days=Decimal("3"),
                production_sequence=99,
                is_final_assembly=True,
            ),
        ]
    )
    db_session.add_all(
        [
            PartCycleBaseline(
                material_no="PART_B001",
                material_desc="机身焊接件",
                core_part_name="焊接件",
                machine_model="MC1-80",
                ref_batch_qty=Decimal("1"),
                cycle_days=Decimal("8"),
                unit_cycle_days=Decimal("8"),
                is_active=True,
            ),
            PartCycleBaseline(
                material_no="PART_B002",
                material_desc="机身焊接件",
                core_part_name="焊接件",
                machine_model="MC1-80",
                ref_batch_qty=Decimal("1"),
                cycle_days=Decimal("8"),
                unit_cycle_days=Decimal("8"),
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 5, 1))
    original_build = orchestrator.part_service.build

    async def build_with_failure(order_line_id: int, machine_schedule_id: int):
        if order_line_id == order_fail.id:
            raise RuntimeError("simulated failure during part scheduling")
        return await original_build(order_line_id, machine_schedule_id)

    monkeypatch.setattr(orchestrator.part_service, "build", build_with_failure)

    result = await orchestrator.schedule_batch([order_ok.id, order_fail.id])
    await db_session.commit()

    ok_machine = (
        (
            await db_session.execute(
                select(MachineScheduleResult).where(MachineScheduleResult.order_line_id == order_ok.id)
            )
        )
        .scalars()
        .first()
    )
    fail_machine = (
        (
            await db_session.execute(
                select(MachineScheduleResult).where(MachineScheduleResult.order_line_id == order_fail.id)
            )
        )
        .scalars()
        .first()
    )
    ok_parts = (
        (await db_session.execute(select(PartScheduleResult).where(PartScheduleResult.order_line_id == order_ok.id)))
        .scalars()
        .all()
    )
    fail_parts = (
        (await db_session.execute(select(PartScheduleResult).where(PartScheduleResult.order_line_id == order_fail.id)))
        .scalars()
        .all()
    )

    assert result["total"] == 2
    assert result["scheduled"] == 1
    assert result["failed"] == 1
    assert ok_machine is not None
    assert len(ok_parts) >= 1
    assert fail_machine is None
    assert fail_parts == []


@pytest.mark.asyncio
async def test_schedule_order_precheck_counts_recursive_self_made_parts(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAPREC",
        sap_line_no="10",
        contract_no="HTREC",
        customer_name="客户REC",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACHREC",
        quantity=Decimal("1"),
        order_no="SOREC",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
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
    db_session.add_all(
        [
            BomRelationSrc(
                machine_material_no="MACHREC",
                plant="1000",
                material_no="MACHREC",
                bom_component_no="ASM_REC",
                bom_component_desc="机身MC1-80",
                bom_level=1,
                is_top_level=True,
                is_self_made=True,
                part_type="自制件",
            ),
            BomRelationSrc(
                machine_material_no="MACHREC",
                plant="1000",
                material_no="ASM_REC",
                bom_component_no="SUB_NON_SELF",
                bom_component_desc="外购子总成",
                bom_level=2,
                is_self_made=False,
                part_type="外购件",
            ),
            BomRelationSrc(
                machine_material_no="MACHREC",
                plant="1000",
                material_no="SUB_NON_SELF",
                bom_component_no="PART_REC",
                bom_component_desc="递归关键件",
                bom_level=3,
                is_self_made=True,
                part_type="自制件",
            ),
        ]
    )
    db_session.add_all(
        [
            AssemblyTimeBaseline(
                machine_model="MC1-80",
                assembly_name="机身",
                assembly_time_days=Decimal("2"),
                production_sequence=1,
                is_final_assembly=False,
            ),
            AssemblyTimeBaseline(
                machine_model="MC1-80",
                assembly_name="整机总装",
                assembly_time_days=Decimal("3"),
                production_sequence=99,
                is_final_assembly=True,
            ),
            PartCycleBaseline(
                material_no="PART_REC",
                material_desc="递归关键件",
                core_part_name="递归关键件",
                machine_model="MC1-80",
                ref_batch_qty=Decimal("1"),
                cycle_days=Decimal("9"),
                unit_cycle_days=Decimal("9"),
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    orchestrator = ScheduleOrchestrator(db_session, today=date(2026, 5, 1))
    result = await orchestrator.schedule_order(order.id)

    assert result["success"] is True
    assert result["machine_schedule"] is not None
    assert len(result["part_schedules"]) == 1
    assert result["part_schedules"][0].part_material_no == "PART_REC"
    assert result["part_schedules"][0].bom_path == "机身(ASM_REC) / 外购子总成(SUB_NON_SELF) / 递归关键件(PART_REC)"
