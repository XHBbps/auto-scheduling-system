from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from app.config import settings
from app.models.assembly_time import AssemblyTimeBaseline
from app.models.bom_relation import BomRelationSrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.scheduler.schedule_orchestrator import ScheduleOrchestrator
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService


async def _seed_scheduled_order(db_session, suffix: str) -> SalesPlanOrderLineSrc:
    order = SalesPlanOrderLineSrc(
        sap_code=f"SAP-SNAPSHOT-{suffix}",
        sap_line_no="10",
        product_model="MC1-80",
        product_series="MC1",
        material_no=f"MACH-{suffix}",
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
            machine_material_no=f"MACH-{suffix}",
            plant="1000",
            material_no=f"MACH-{suffix}",
            bom_component_no=f"ASM-{suffix}",
            bom_component_desc="机身总成",
            bom_level=1,
            is_self_made=True,
            part_type="自产件",
        )
    )
    db_session.add(
        BomRelationSrc(
            machine_material_no=f"MACH-{suffix}",
            plant="1000",
            material_no=f"ASM-{suffix}",
            bom_component_no=f"PART-{suffix}",
            bom_component_desc="机身焊接件",
            bom_level=2,
            is_self_made=True,
            part_type="自产件",
        )
    )
    await db_session.commit()

    result = await ScheduleOrchestrator(db_session).schedule_order(order.id)
    await db_session.commit()
    assert result["success"] is True
    return order


async def _seed_schedulable_order(db_session, suffix: str) -> SalesPlanOrderLineSrc:
    order = SalesPlanOrderLineSrc(
        sap_code=f"SAP-SNAPSHOT-BATCH-{suffix}",
        sap_line_no="10",
        product_model="MC1-80",
        product_series="MC1",
        material_no=f"MACH-BATCH-{suffix}",
        delivery_plant="1000",
        quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 20),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)
    await db_session.flush()
    return order


@pytest.mark.asyncio
async def test_refresh_one_builds_schedulable_snapshot(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP-SNAPSHOT-1",
        sap_line_no="10",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACH-S1",
        delivery_plant="1000",
        quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 20),
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
        BomRelationSrc(
            machine_material_no="MACH-S1",
            plant="1000",
            material_no="MACH-S1",
            bom_component_no="ASM-S1",
            bom_component_desc="机身总成",
            bom_level=1,
            is_self_made=True,
            part_type="自产件",
        )
    )
    await db_session.commit()

    snapshot = await ScheduleSnapshotRefreshService(db_session).refresh_one(
        order.id,
        source="test",
        reason="initial_refresh",
    )
    await db_session.commit()

    assert snapshot is not None
    assert snapshot.schedule_status == "schedulable"
    assert snapshot.machine_schedule_id is None
    assert snapshot.plant == "1000"


@pytest.mark.asyncio
async def test_refresh_one_distinguishes_bom_by_plant(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP-SNAPSHOT-PLANT-1",
        sap_line_no="10",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACH-PLANT-1",
        delivery_plant="1200",
        quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 20),
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
        BomRelationSrc(
            machine_material_no="MACH-PLANT-1",
            plant="1000",
            material_no="MACH-PLANT-1",
            bom_component_no="ASM-PLANT-1",
            bom_component_desc="机身总成",
            bom_level=1,
            is_self_made=True,
            part_type="自产件",
        )
    )
    await db_session.commit()

    snapshot = await ScheduleSnapshotRefreshService(db_session).refresh_one(
        order.id,
        source="test",
        reason="plant_scope_refresh",
    )
    await db_session.commit()

    assert snapshot is not None
    assert snapshot.schedule_status == "missing_bom"
    assert snapshot.plant == "1200"


@pytest.mark.asyncio
async def test_refresh_one_marks_scheduled_result_stale_when_source_changes(db_session):
    order = await _seed_scheduled_order(db_session, "S2")

    order.confirmed_delivery_date = datetime(2026, 3, 25)
    await db_session.flush()

    snapshot = await ScheduleSnapshotRefreshService(db_session).refresh_one(
        order.id,
        source="test",
        reason="reconcile",
    )
    await db_session.commit()

    machine_schedule = (
        await db_session.execute(select(MachineScheduleResult).where(MachineScheduleResult.order_line_id == order.id))
    ).scalar_one()
    stored_snapshot = (
        await db_session.execute(select(OrderScheduleSnapshot).where(OrderScheduleSnapshot.order_line_id == order.id))
    ).scalar_one()

    assert machine_schedule is not None
    assert snapshot.schedule_status == "scheduled_stale"
    assert stored_snapshot.status_reason == "sales_plan_changed:confirmed_delivery_date"


@pytest.mark.asyncio
async def test_mark_scheduled_rejects_mismatched_machine_schedule_binding(db_session):
    order_a = await _seed_schedulable_order(db_session, "MS-A")
    order_b = await _seed_schedulable_order(db_session, "MS-B")
    machine = MachineScheduleResult(
        order_line_id=order_b.id,
        product_model="MC1-80",
        planned_start_date=datetime(2026, 4, 1),
        planned_end_date=datetime(2026, 6, 30),
        machine_cycle_days=Decimal("60"),
        machine_assembly_days=Decimal("3"),
        schedule_status="scheduled",
    )
    db_session.add(machine)
    await db_session.commit()

    service = ScheduleSnapshotRefreshService(db_session)

    with pytest.raises(ValueError, match="does not belong"):
        await service.mark_scheduled(
            order_a.id,
            machine_schedule_id=machine.id,
            source="test",
            reason="mark_scheduled_mismatch",
        )


@pytest.mark.asyncio
async def test_refresh_one_keeps_scheduled_when_only_product_series_changes(db_session):
    order = await _seed_scheduled_order(db_session, "S3")
    order.product_series = "MC2"
    await db_session.flush()

    snapshot = await ScheduleSnapshotRefreshService(db_session).refresh_one(
        order.id,
        source="test",
        reason="reconcile",
    )
    await db_session.commit()

    assert snapshot.schedule_status == "scheduled"


@pytest.mark.asyncio
async def test_refresh_one_keeps_scheduled_when_bom_is_missing_after_schedule(db_session):
    order = await _seed_scheduled_order(db_session, "S4")
    await db_session.execute(delete(BomRelationSrc).where(BomRelationSrc.machine_material_no == "MACH-S4"))
    await db_session.commit()

    snapshot = await ScheduleSnapshotRefreshService(db_session).refresh_one(
        order.id,
        source="test",
        reason="reconcile",
    )
    await db_session.commit()

    assert snapshot.schedule_status == "scheduled"


@pytest.mark.asyncio
async def test_refresh_one_reuses_loaded_snapshot_without_second_lookup(monkeypatch, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP-SNAPSHOT-S4A",
        sap_line_no="10",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACH-S4A",
        quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 20),
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
        BomRelationSrc(
            machine_material_no="MACH-S4A",
            plant="1000",
            material_no="MACH-S4A",
            bom_component_no="ASM-S4A",
            bom_component_desc="机身总成",
            bom_level=1,
            is_self_made=True,
            part_type="自产件",
        )
    )
    await db_session.flush()
    db_session.add(
        OrderScheduleSnapshot(
            order_line_id=order.id,
            schedule_status="pending_trigger",
            status_reason="stale_seed",
        )
    )
    await db_session.commit()

    service = ScheduleSnapshotRefreshService(db_session)
    original_find = service.snapshot_repo.find_by_order_line_id
    lookup_count = 0

    async def counting_find(order_line_id: int):
        nonlocal lookup_count
        lookup_count += 1
        return await original_find(order_line_id)

    monkeypatch.setattr(service.snapshot_repo, "find_by_order_line_id", counting_find)

    snapshot = await service.refresh_one(
        order.id,
        source="test",
        reason="reuse_existing_snapshot",
    )
    await db_session.commit()

    assert snapshot is not None
    assert snapshot.schedule_status == "schedulable"
    assert lookup_count == 1


@pytest.mark.asyncio
async def test_refresh_batch_uses_prefetched_path_without_refresh_one(monkeypatch, db_session):
    scheduled_order = await _seed_scheduled_order(db_session, "S5")

    dynamic_order = SalesPlanOrderLineSrc(
        sap_code="SAP-SNAPSHOT-S6",
        sap_line_no="10",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACH-S6",
        quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 20),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(dynamic_order)
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH-S6",
            plant="1000",
            material_no="MACH-S6",
            bom_component_no="ASM-S6",
            bom_component_desc="机身总成",
            bom_level=1,
            is_self_made=True,
            part_type="自产件",
        )
    )
    await db_session.commit()

    service = ScheduleSnapshotRefreshService(db_session)

    async def fail_refresh_one(*args, **kwargs):
        raise AssertionError("refresh_batch should not call refresh_one one-by-one")

    async def fail_find_by_order_line_id(*args, **kwargs):
        raise AssertionError("refresh_batch should reuse prefetched snapshots without per-row lookup")

    monkeypatch.setattr(service, "refresh_one", fail_refresh_one)
    monkeypatch.setattr(service.snapshot_repo, "find_by_order_line_id", fail_find_by_order_line_id)

    result = await service.refresh_batch(
        [scheduled_order.id, dynamic_order.id],
        source="test",
        reason="batch_refresh",
    )
    await db_session.commit()

    snapshots = (
        (
            await db_session.execute(
                select(OrderScheduleSnapshot).where(
                    OrderScheduleSnapshot.order_line_id.in_([scheduled_order.id, dynamic_order.id])
                )
            )
        )
        .scalars()
        .all()
    )
    status_map = {snapshot.order_line_id: snapshot.schedule_status for snapshot in snapshots}

    assert result["total"] == 2
    assert result["refreshed"] == 2
    assert result["scheduled"] == 1
    assert status_map[scheduled_order.id] == "scheduled"
    assert status_map[dynamic_order.id] == "schedulable"


@pytest.mark.asyncio
async def test_rebuild_all_open_snapshots_processes_known_ids_in_batches(monkeypatch, db_session):
    orders = []
    for suffix in ("R1", "R2", "R3"):
        orders.append(await _seed_schedulable_order(db_session, suffix))

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
    db_session.add_all(
        [
            BomRelationSrc(
                machine_material_no=f"MACH-BATCH-{suffix}",
                plant="1000",
                material_no=f"MACH-BATCH-{suffix}",
                bom_component_no=f"ASM-BATCH-{suffix}",
                bom_component_desc="机身总成",
                bom_level=1,
                is_self_made=True,
                part_type="自产件",
            )
            for suffix in ("R1", "R2", "R3")
        ]
    )
    await db_session.commit()

    service = ScheduleSnapshotRefreshService(db_session)
    observed_batches: list[list[int]] = []

    async def recording_refresh_batch(order_line_ids, **kwargs):
        batch = list(order_line_ids)
        observed_batches.append(batch)
        return {
            "total": len(batch),
            "refreshed": len(batch),
            "scheduled": 0,
            "scheduled_stale": 0,
            "deleted": 0,
        }

    monkeypatch.setattr(settings, "snapshot_refresh_batch_size", 2)
    monkeypatch.setattr(service, "refresh_batch", recording_refresh_batch)

    result = await service.rebuild_all_open_snapshots(
        source="test",
        reason="batch_rebuild",
    )

    assert observed_batches == [[orders[0].id, orders[1].id], [orders[2].id]]
    assert result == {
        "total": 3,
        "refreshed": 3,
        "scheduled": 0,
        "scheduled_stale": 0,
        "deleted": 0,
    }


@pytest.mark.asyncio
async def test_get_observability_summary_counts_known_orders_without_full_id_scan(monkeypatch, db_session):
    order = await _seed_schedulable_order(db_session, "OBS")
    db_session.add(
        MachineScheduleResult(
            order_line_id=order.id,
            product_model="MC1-80",
            material_no="MACH-BATCH-OBS",
            schedule_status="scheduled",
            machine_cycle_days=Decimal("1"),
            machine_assembly_days=Decimal("1"),
        )
    )
    await db_session.commit()

    service = ScheduleSnapshotRefreshService(db_session)

    async def fail_list_all_known_order_line_ids():
        raise AssertionError("get_observability_summary should count known orders in SQL")

    monkeypatch.setattr(service, "_list_all_known_order_line_ids", fail_list_all_known_order_line_ids)

    summary = await service.get_observability_summary()

    assert summary["summary"]["known_order_count"] == 1


@pytest.mark.asyncio
async def test_get_observability_summary_uses_aggregated_snapshot_stats(monkeypatch, db_session):
    service = ScheduleSnapshotRefreshService(db_session)

    async def fake_get_observability_aggregates():
        return {
            "known_order_count": 4,
            "total_snapshots": 3,
            "oldest_refreshed_at": None,
            "latest_refreshed_at": None,
            "status_counts": {"scheduled": 2, "missing_bom": 1},
            "refresh_source_counts": {"seed": 3},
        }

    async def fail_count_all():
        raise AssertionError("get_observability_summary should not query total snapshots separately")

    async def fail_count_by_schedule_status():
        raise AssertionError("get_observability_summary should not query status counts separately")

    async def fail_count_by_refresh_source():
        raise AssertionError("get_observability_summary should not query refresh source counts separately")

    async def fail_get_refresh_bounds():
        raise AssertionError("get_observability_summary should not query refresh bounds separately")

    async def fail_count_known_orders():
        raise AssertionError("get_observability_summary should not count known orders separately")

    monkeypatch.setattr(service.snapshot_repo, "get_observability_aggregates", fake_get_observability_aggregates)
    monkeypatch.setattr(service.snapshot_repo, "count_all", fail_count_all)
    monkeypatch.setattr(service.snapshot_repo, "count_by_schedule_status", fail_count_by_schedule_status)
    monkeypatch.setattr(service.snapshot_repo, "count_by_refresh_source", fail_count_by_refresh_source)
    monkeypatch.setattr(service.snapshot_repo, "get_refresh_bounds", fail_get_refresh_bounds)
    monkeypatch.setattr(service, "_count_all_known_order_line_ids", fail_count_known_orders)

    summary = await service.get_observability_summary()

    assert summary["summary"]["total_snapshots"] == 3
    assert summary["summary"]["status_counts"] == {"scheduled": 2, "missing_bom": 1}
    assert summary["summary"]["refresh_source_counts"] == {"seed": 3}
    assert summary["summary"]["coverage_ratio"] == 0.75


@pytest.mark.asyncio
async def test_fast_seed_all_processes_known_ids_in_batches(monkeypatch, db_session):
    orders = []
    for suffix in ("F1", "F2", "F3"):
        orders.append(await _seed_schedulable_order(db_session, suffix))

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
    db_session.add_all(
        [
            BomRelationSrc(
                machine_material_no=f"MACH-BATCH-{suffix}",
                plant="1000",
                material_no=f"MACH-BATCH-{suffix}",
                bom_component_no=f"ASM-BATCH-{suffix}",
                bom_component_desc="机身总成",
                bom_level=1,
                is_self_made=True,
                part_type="自产件",
            )
            for suffix in ("F1", "F2", "F3")
        ]
    )
    await db_session.commit()

    service = ScheduleSnapshotRefreshService(db_session)
    original_preload = service._preload_refresh_batch_dependencies
    observed_batches: list[tuple[list[int], bool, object | None]] = []
    shared_dynamic_context = {
        "bom_material_pairs": {("MACH-BATCH-F1", "1000")},
        "baselines_by_model": {},
        "calendar": {},
    }

    async def fake_build_shared_dynamic_context_for_known_orders():
        return shared_dynamic_context

    async def recording_preload(order_line_ids, *, include_snapshot_map=True, shared_dynamic_context=None):
        observed_batches.append((list(order_line_ids), include_snapshot_map, shared_dynamic_context))
        return await original_preload(
            order_line_ids,
            include_snapshot_map=include_snapshot_map,
            shared_dynamic_context=shared_dynamic_context,
        )

    monkeypatch.setattr(settings, "snapshot_refresh_batch_size", 2)
    monkeypatch.setattr(
        service,
        "_build_shared_dynamic_context_for_known_orders",
        fake_build_shared_dynamic_context_for_known_orders,
    )
    monkeypatch.setattr(service, "_preload_refresh_batch_dependencies", recording_preload)

    seeded = await service._fast_seed_all(
        source="test",
        reason="fast_seed_batching",
    )
    await db_session.commit()

    snapshots = (
        (await db_session.execute(select(OrderScheduleSnapshot).order_by(OrderScheduleSnapshot.order_line_id.asc())))
        .scalars()
        .all()
    )

    assert seeded == 3
    assert [snapshot.order_line_id for snapshot in snapshots] == [order.id for order in orders]
    assert observed_batches == [
        ([orders[0].id, orders[1].id], False, shared_dynamic_context),
        ([orders[2].id], False, shared_dynamic_context),
    ]


@pytest.mark.asyncio
async def test_preload_refresh_batch_dependencies_reuses_provided_shared_context(monkeypatch, db_session):
    order = await _seed_schedulable_order(db_session, "SHARED")
    await db_session.commit()

    service = ScheduleSnapshotRefreshService(db_session)
    shared_dynamic_context = {
        "bom_material_pairs": {("MACH-BATCH-SHARED", "1000")},
        "baselines_by_model": {"MC1-80": []},
        "calendar": {},
    }

    async def fail_load_machine_bom_pairs():
        raise AssertionError("shared dynamic context should avoid reloading bom pairs")

    async def fail_load_machine_cycle_baselines():
        raise AssertionError("shared dynamic context should avoid reloading baselines")

    async def fail_load_seed_calendar(*args, **kwargs):
        raise AssertionError("shared dynamic context should avoid rebuilding calendar")

    monkeypatch.setattr(service, "_load_machine_bom_pairs", fail_load_machine_bom_pairs)
    monkeypatch.setattr(service, "_load_machine_cycle_baselines", fail_load_machine_cycle_baselines)
    monkeypatch.setattr(service, "_load_seed_calendar", fail_load_seed_calendar)

    preloaded = await service._preload_refresh_batch_dependencies(
        [order.id],
        include_snapshot_map=False,
        shared_dynamic_context=shared_dynamic_context,
    )

    assert preloaded["dynamic_context"] is shared_dynamic_context


@pytest.mark.asyncio
async def test_rebuild_all_open_snapshots_reuses_shared_dynamic_context(monkeypatch, db_session):
    orders = []
    for suffix in ("RC1", "RC2", "RC3"):
        orders.append(await _seed_schedulable_order(db_session, suffix))

    service = ScheduleSnapshotRefreshService(db_session)
    observed_contexts: list[object | None] = []
    shared_dynamic_context = {"calendar": {}, "bom_material_pairs": set(), "baselines_by_model": {}}

    async def fake_build_shared_dynamic_context_for_known_orders():
        return shared_dynamic_context

    async def recording_refresh_batch(order_line_ids, **kwargs):
        observed_contexts.append(kwargs.get("shared_dynamic_context"))
        batch = list(order_line_ids)
        return {
            "total": len(batch),
            "refreshed": len(batch),
            "scheduled": 0,
            "scheduled_stale": 0,
            "deleted": 0,
        }

    monkeypatch.setattr(settings, "snapshot_refresh_batch_size", 2)
    monkeypatch.setattr(
        service,
        "_build_shared_dynamic_context_for_known_orders",
        fake_build_shared_dynamic_context_for_known_orders,
    )
    monkeypatch.setattr(service, "refresh_batch", recording_refresh_batch)

    result = await service.rebuild_all_open_snapshots(
        source="test",
        reason="shared_context_rebuild",
    )

    assert observed_contexts == [shared_dynamic_context, shared_dynamic_context]
    assert result == {
        "total": 3,
        "refreshed": 3,
        "scheduled": 0,
        "scheduled_stale": 0,
        "deleted": 0,
    }


@pytest.mark.asyncio
async def test_merge_order_line_ids_deduplicates_and_sorts(db_session):
    order_a = await _seed_schedulable_order(db_session, "MERGE-A")
    order_b = await _seed_schedulable_order(db_session, "MERGE-B")
    await db_session.commit()

    db_session.add(
        MachineScheduleResult(
            order_line_id=order_b.id,
            product_model="MC1-80",
            material_no="MACH-BATCH-MERGE-B",
            schedule_status="scheduled",
            machine_cycle_days=Decimal("1"),
            machine_assembly_days=Decimal("1"),
        )
    )
    db_session.add(
        MachineScheduleResult(
            order_line_id=order_a.id + 10,
            product_model="MC1-80",
            material_no="MACH-BATCH-MERGE-X",
            schedule_status="scheduled",
            machine_cycle_days=Decimal("1"),
            machine_assembly_days=Decimal("1"),
        )
    )
    await db_session.commit()

    service = ScheduleSnapshotRefreshService(db_session)
    order_line_ids = await service._merge_order_line_ids(
        select(SalesPlanOrderLineSrc.id.label("order_line_id")).where(
            SalesPlanOrderLineSrc.id.in_([order_b.id, order_a.id])
        ),
        select(MachineScheduleResult.order_line_id.label("order_line_id")).where(
            MachineScheduleResult.order_line_id.in_([order_b.id, order_a.id + 10])
        ),
    )

    assert order_line_ids == [order_a.id, order_b.id, order_a.id + 10]


@pytest.mark.asyncio
async def test_refresh_by_bom_component_no_uses_db_side_subquery_and_machine_model_filter(monkeypatch, db_session):
    order_a = await _seed_schedulable_order(db_session, "BOM-A")
    order_b = await _seed_schedulable_order(db_session, "BOM-B")
    order_c = await _seed_schedulable_order(db_session, "BOM-C")
    order_c.product_model = "MC2-100"

    db_session.add_all(
        [
            BomRelationSrc(
                machine_material_no="MACH-BATCH-BOM-A",
                plant="1000",
                material_no="MACH-BATCH-BOM-A",
                bom_component_no="PART-HOT",
                bom_component_desc="热点零件A",
                bom_level=1,
                is_self_made=True,
                part_type="自产件",
            ),
            BomRelationSrc(
                machine_material_no="MACH-BATCH-BOM-B",
                plant="1000",
                material_no="MACH-BATCH-BOM-B",
                bom_component_no="PART-HOT",
                bom_component_desc="热点零件B",
                bom_level=1,
                is_self_made=True,
                part_type="自产件",
            ),
            BomRelationSrc(
                machine_material_no="MACH-BATCH-BOM-C",
                plant="1000",
                material_no="MACH-BATCH-BOM-C",
                bom_component_no="PART-HOT",
                bom_component_desc="热点零件C",
                bom_level=1,
                is_self_made=True,
                part_type="自产件",
            ),
        ]
    )
    await db_session.commit()

    service = ScheduleSnapshotRefreshService(db_session)
    captured: dict[str, list[int]] = {}

    async def recording_refresh_batch(order_line_ids, **kwargs):
        captured["order_line_ids"] = list(order_line_ids)
        return {
            "total": len(captured["order_line_ids"]),
            "refreshed": len(captured["order_line_ids"]),
            "scheduled": 0,
            "scheduled_stale": 0,
            "deleted": 0,
        }

    monkeypatch.setattr(service, "refresh_batch", recording_refresh_batch)

    result = await service.refresh_by_bom_component_no(
        "PART-HOT",
        source="test",
        reason="bom_component_hotspot",
        machine_model="MC1-80",
    )

    assert captured["order_line_ids"] == [order_a.id, order_b.id]
    assert result["total"] == 2


@pytest.mark.asyncio
async def test_refresh_by_part_type_uses_db_side_subquery(monkeypatch, db_session):
    order_a = await _seed_schedulable_order(db_session, "TYPE-A")
    order_b = await _seed_schedulable_order(db_session, "TYPE-B")
    await db_session.commit()

    db_session.add_all(
        [
            BomRelationSrc(
                machine_material_no="MACH-BATCH-TYPE-A",
                plant="1000",
                material_no="MACH-BATCH-TYPE-A",
                bom_component_no="PART-TYPE-A",
                bom_component_desc="机身焊接件",
                bom_level=1,
                is_self_made=True,
                part_type="自产件",
            ),
            BomRelationSrc(
                machine_material_no="MACH-BATCH-TYPE-B",
                plant="1000",
                material_no="MACH-BATCH-TYPE-B",
                bom_component_no="PART-TYPE-B",
                bom_component_desc="机身机加工件",
                bom_level=1,
                is_self_made=True,
                part_type="自产件",
            ),
        ]
    )
    await db_session.commit()

    service = ScheduleSnapshotRefreshService(db_session)
    captured: dict[str, list[int]] = {}

    async def recording_refresh_batch(order_line_ids, **kwargs):
        captured["order_line_ids"] = list(order_line_ids)
        return {
            "total": len(captured["order_line_ids"]),
            "refreshed": len(captured["order_line_ids"]),
            "scheduled": 0,
            "scheduled_stale": 0,
            "deleted": 0,
        }

    monkeypatch.setattr(service, "refresh_batch", recording_refresh_batch)

    result = await service.refresh_by_part_type(
        "机身",
        source="test",
        reason="part_type_hotspot",
    )

    assert captured["order_line_ids"] == [order_a.id, order_b.id]
    assert result["total"] == 2
