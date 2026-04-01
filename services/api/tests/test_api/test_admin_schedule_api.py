import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy import select

from app.models.data_issue import DataIssueRecord
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.part_schedule_result import PartScheduleResult
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.assembly_time import AssemblyTimeBaseline
from app.models.bom_relation import BomRelationSrc
from app.models.part_cycle_baseline import PartCycleBaseline
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService


@pytest.mark.asyncio
async def test_run_schedule(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH001", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 20),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("1"),
        sample_count=5, is_active=True,
    ))
    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80", assembly_name="整机总装",
        assembly_time_days=Decimal("3"), is_final_assembly=True,
        production_sequence=99,
    ))
    await db_session.commit()

    resp = await app_client.post("/api/admin/schedule/run", json={
        "order_line_ids": [order.id],
    })
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1


@pytest.mark.asyncio
async def test_run_schedule_without_order_ids_auto_finds_schedulable_orders(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001-AUTO", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH001-AUTO", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 20),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
        order_no="SO-AUTO-1",
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("1"),
        sample_count=5, is_active=True,
    ))
    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80", assembly_name="整机总装",
        assembly_time_days=Decimal("3"), is_final_assembly=True,
        production_sequence=99,
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH001-AUTO", plant="1000",
        material_no="MACH001-AUTO", bom_component_no="ASM001-AUTO",
        bom_component_desc="机身MC1-80", bom_level=1,
        is_self_made=True, part_type="自产件",
    ))
    await db_session.commit()

    resp = await app_client.post("/api/admin/schedule/run", json={})
    body = resp.json()

    machine_schedule = (
        await db_session.execute(
            select(MachineScheduleResult).where(MachineScheduleResult.order_line_id == order.id)
        )
    ).scalars().first()

    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["success_count"] == 1
    assert machine_schedule is not None
    assert machine_schedule.schedule_status == "scheduled"


@pytest.mark.asyncio
async def test_run_schedule_missing_bom_returns_failed_and_creates_issue(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP002", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH404", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("60"),
        sample_count=5, is_active=True,
    ))
    await db_session.commit()

    resp = await app_client.post("/api/admin/schedule/run", json={
        "order_line_ids": [order.id],
    })
    body = resp.json()

    issue = (
        await db_session.execute(
            select(DataIssueRecord).where(DataIssueRecord.biz_key == str(order.id))
        )
    ).scalars().first()

    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["success_count"] == 0
    assert body["data"]["fail_count"] == 1
    assert issue is not None
    assert issue.issue_type == "BOM缺失"


@pytest.mark.asyncio
async def test_run_schedule_missing_machine_cycle_marks_abnormal_and_creates_issue(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP003", sap_line_no="10",
        product_model="PSP-80B(二级传动)", product_series="PSP",
        material_no="MACH777", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)
    db_session.add(BomRelationSrc(
        machine_material_no="MACH777", plant="1000",
        material_no="MACH777", bom_component_no="ASM777",
        bom_component_desc="机身PSP-80B", bom_level=2,
        is_self_made=True, part_type="自产件",
    ))
    db_session.add(AssemblyTimeBaseline(
        machine_model="PSP-80B(二级传动)", assembly_name="整机总装",
        assembly_time_days=Decimal("3"), is_final_assembly=True,
        production_sequence=99,
    ))
    await db_session.commit()

    resp = await app_client.post("/api/admin/schedule/run", json={
        "order_line_ids": [order.id],
    })
    body = resp.json()

    issue = (
        await db_session.execute(
            select(DataIssueRecord).where(DataIssueRecord.biz_key == str(order.id))
        )
    ).scalars().first()
    machine_schedule = (
        await db_session.execute(
            select(MachineScheduleResult).where(MachineScheduleResult.order_line_id == order.id)
        )
    ).scalars().first()

    assert body["code"] == 0
    assert body["data"]["success_count"] == 1
    assert issue is not None
    assert issue.issue_type == "整机周期基准缺失"
    assert machine_schedule is not None
    assert machine_schedule.warning_level == "abnormal"
    assert machine_schedule.issue_flags["machine_cycle_default"] is True


@pytest.mark.asyncio
async def test_run_schedule_pending_drawing_creates_issue(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP004", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH004", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=False,
        order_no="SO004",
    )
    db_session.add(order)
    await db_session.commit()

    resp = await app_client.post("/api/admin/schedule/run", json={
        "order_line_ids": [order.id],
    })
    body = resp.json()

    issue = (
        await db_session.execute(
            select(DataIssueRecord).where(DataIssueRecord.biz_key == str(order.id))
        )
    ).scalars().first()

    assert body["code"] == 0
    assert body["data"]["success_count"] == 0
    assert body["data"]["fail_count"] == 1
    assert issue is not None
    assert issue.issue_type == "发图状态未完成"


@pytest.mark.asyncio
async def test_run_schedule_missing_part_cycle_marks_part_and_machine_abnormal(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP005", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH005", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 20),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
        order_no="SO005",
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("1"),
        sample_count=5, is_active=True,
    ))
    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80", assembly_name="整机总装",
        assembly_time_days=Decimal("3"), is_final_assembly=True,
        production_sequence=99,
    ))
    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80", assembly_name="机身",
        assembly_time_days=Decimal("2"), is_final_assembly=False,
        production_sequence=1,
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH005", plant="1000",
        material_no="MACH005", bom_component_no="ASM005",
        bom_component_desc="机身MC1-80", bom_level=1,
        is_self_made=True, part_type="自产件",
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH005", plant="1000",
        material_no="ASM005", bom_component_no="PART005",
        bom_component_desc="机身焊接件", bom_level=2,
        is_self_made=True, part_type="自产件",
    ))
    await db_session.commit()

    resp = await app_client.post("/api/admin/schedule/run", json={
        "order_line_ids": [order.id],
    })
    body = resp.json()

    issue = (
        await db_session.execute(
            select(DataIssueRecord).where(
                DataIssueRecord.biz_key == str(order.id),
                DataIssueRecord.issue_type == "零件周期基准缺失",
            )
        )
    ).scalars().first()
    machine_schedule = (
        await db_session.execute(
            select(MachineScheduleResult).where(MachineScheduleResult.order_line_id == order.id)
        )
    ).scalars().first()
    part_schedule = (
        await db_session.execute(
            select(PartScheduleResult).where(PartScheduleResult.order_line_id == order.id)
        )
    ).scalars().first()

    assert body["code"] == 0
    assert body["data"]["success_count"] == 1
    assert issue is not None
    assert machine_schedule is not None
    assert machine_schedule.warning_level == "abnormal"
    assert machine_schedule.issue_flags["part_schedule_default"] is True
    assert part_schedule is not None
    assert part_schedule.warning_level == "abnormal"
    assert part_schedule.issue_flags["part_cycle_default"] is True


@pytest.mark.asyncio
async def test_run_one_part_schedule_succeeds_for_single_order(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP-PART-001", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH-PART-001", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 20),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
        order_no="SO-PART-001",
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("1"),
        sample_count=5, is_active=True,
    ))
    db_session.add_all([
        AssemblyTimeBaseline(
            machine_model="MC1-80", assembly_name="总装",
            assembly_time_days=Decimal("3"), is_final_assembly=True,
            production_sequence=99,
        ),
        AssemblyTimeBaseline(
            machine_model="MC1-80", assembly_name="泵组",
            assembly_time_days=Decimal("2"), is_final_assembly=False,
            production_sequence=1,
        ),
    ])
    db_session.add_all([
        BomRelationSrc(
            machine_material_no="MACH-PART-001", plant="1000",
            material_no="MACH-PART-001", bom_component_no="ASM-PART-001",
            bom_component_desc="泵组总成", bom_level=1,
            is_self_made=True, part_type="整机",
        ),
        BomRelationSrc(
            machine_material_no="MACH-PART-001", plant="1000",
            material_no="ASM-PART-001", bom_component_no="PART-PART-001",
            bom_component_desc="泵体铸件", bom_level=2,
            is_self_made=True, part_type="零件",
        ),
    ])
    db_session.add(PartCycleBaseline(
        material_no="PART-PART-001", material_desc="泵体铸件",
        core_part_name="泵体", machine_model="MC1-80",
        ref_batch_qty=Decimal("1"), cycle_days=Decimal("8"),
        unit_cycle_days=Decimal("8"), is_active=True,
    ))
    await db_session.commit()

    resp = await app_client.post("/api/admin/schedule/run-one-part", json={
        "order_line_id": order.id,
    })
    body = resp.json()

    machine_schedule = (
        await db_session.execute(
            select(MachineScheduleResult).where(MachineScheduleResult.order_line_id == order.id)
        )
    ).scalars().first()
    part_rows = (
        await db_session.execute(
            select(PartScheduleResult).where(PartScheduleResult.order_line_id == order.id)
        )
    ).scalars().all()

    assert body["code"] == 0
    assert body["data"]["success"] is True
    assert body["data"]["precheck_passed"] is True
    assert body["data"]["machine_schedule_built"] is True
    assert body["data"]["part_schedule_built"] is True
    assert machine_schedule is not None
    assert len(part_rows) >= 1


@pytest.mark.asyncio
async def test_run_one_part_schedule_blocks_when_bom_missing(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP-PART-404", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH-PART-404", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
        order_no="SO-PART-404",
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("60"),
        sample_count=5, is_active=True,
    ))
    await db_session.commit()

    resp = await app_client.post("/api/admin/schedule/run-one-part", json={
        "order_line_id": order.id,
    })
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["success"] is False
    assert body["data"]["precheck_passed"] is False
    assert body["data"]["status"] == "missing_bom"
    assert body["data"]["validation_items"][0]["code"] == "missing_bom"


@pytest.mark.asyncio
async def test_run_one_part_schedule_blocks_when_part_data_missing(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP-PART-NOCHILD", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH-PART-NOCHILD", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 20),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
        order_no="SO-PART-NOCHILD",
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("1"),
        sample_count=5, is_active=True,
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH-PART-NOCHILD", plant="1000",
        material_no="MACH-PART-NOCHILD", bom_component_no="ASM-PART-NOCHILD",
        bom_component_desc="泵组总成", bom_level=1,
        is_self_made=True, part_type="整机",
    ))
    await db_session.commit()

    resp = await app_client.post("/api/admin/schedule/run-one-part", json={
        "order_line_id": order.id,
    })
    body = resp.json()

    machine_schedule = (
        await db_session.execute(
            select(MachineScheduleResult).where(MachineScheduleResult.order_line_id == order.id)
        )
    ).scalars().first()

    assert body["code"] == 0
    assert body["data"]["success"] is False
    assert body["data"]["precheck_passed"] is False
    assert body["data"]["status"] == "missing_part_data"
    assert body["data"]["validation_items"][0]["code"] == "missing_part_data"
    assert machine_schedule is None


@pytest.mark.asyncio
async def test_get_snapshot_observability_returns_healthy_summary(app_client, db_session):
    ScheduleSnapshotRefreshService.reset_runtime_observations()

    order = SalesPlanOrderLineSrc(
        sap_code="SAP-OBS-1", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH-OBS-1", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 20),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("1"),
        sample_count=5, is_active=True,
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MACH-OBS-1", plant="1000",
        material_no="MACH-OBS-1", bom_component_no="ASM-OBS-1",
        bom_component_desc="机身", bom_level=1,
        is_self_made=True, part_type="自产件",
    ))
    await db_session.commit()

    await ScheduleSnapshotRefreshService(db_session).rebuild_all_open_snapshots(
        source="test",
        reason="observability_test",
    )
    await db_session.commit()

    resp = await app_client.get("/api/admin/schedule/snapshots/observability")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["health"]["status"] == "healthy"
    assert body["data"]["summary"]["known_order_count"] == 1
    assert body["data"]["summary"]["total_snapshots"] == 1
    assert body["data"]["summary"]["coverage_ratio"] == 1.0
    assert body["data"]["summary"]["status_counts"]["schedulable"] == 1
    assert body["data"]["runtime_observations"][0]["operation"] == "rebuild_all_open_snapshots"


@pytest.mark.asyncio
async def test_get_snapshot_observability_warns_when_snapshot_empty(app_client, db_session):
    ScheduleSnapshotRefreshService.reset_runtime_observations()

    order = SalesPlanOrderLineSrc(
        sap_code="SAP-OBS-EMPTY", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH-OBS-EMPTY", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 20),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)
    await db_session.commit()

    resp = await app_client.get("/api/admin/schedule/snapshots/observability")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["health"]["status"] == "critical"
    assert body["data"]["summary"]["known_order_count"] == 1
    assert body["data"]["summary"]["total_snapshots"] == 0
    assert any(alert["code"] == "snapshot_empty" for alert in body["data"]["health"]["alerts"])
