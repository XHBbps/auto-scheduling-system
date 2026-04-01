import pytest
from datetime import datetime
from decimal import Decimal

from app.baseline.part_cycle_baseline_service import PartCycleBaselineService
from app.models.production_order import ProductionOrderHistorySrc
from app.repository.part_cycle_baseline_repo import PartCycleBaselineRepo


@pytest.mark.asyncio
async def test_build_baseline_grouped_by_part_type_and_machine_model(db_session):
    db_session.add_all(
        [
            ProductionOrderHistorySrc(
                production_order_no="PO001",
                material_no="PART-001",
                material_desc="右导轨总成MC1-25.1-13",
                machine_model="MC1-80",
                plant="1000",
                start_time_actual=datetime(2026, 1, 1),
                finish_time_actual=datetime(2026, 1, 31),
                production_qty=Decimal("1"),
                order_status="已完工",
            ),
            ProductionOrderHistorySrc(
                production_order_no="PO002",
                material_no="PART-002",
                material_desc="右导轨总成MC1-25.1-15",
                machine_model="MC1-80",
                plant="1000",
                start_time_actual=datetime(2026, 2, 1),
                finish_time_actual=datetime(2026, 2, 21),
                production_qty=Decimal("1"),
                order_status="已完工",
            ),
            ProductionOrderHistorySrc(
                production_order_no="PO006",
                material_no="PART-006",
                material_desc="右导轨总成MC1-25.1-16",
                machine_model="MC1-80",
                plant="1000",
                start_time_actual=datetime(2026, 3, 1),
                finish_time_actual=datetime(2026, 3, 26),
                production_qty=Decimal("1"),
                order_status="已完工",
            ),
        ]
    )
    await db_session.commit()

    service = PartCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    repo = PartCycleBaselineRepo(db_session)
    baseline = await repo.find_by_model_and_part_type("MC1-80", "右导轨总成", "1000")

    assert baseline is not None
    assert baseline.material_no == "右导轨总成"
    assert baseline.core_part_name == "右导轨总成"
    assert baseline.plant == "1000"
    assert baseline.match_rule == "part_type_exact_with_plant"
    assert baseline.cycle_days == Decimal("25.0")
    assert baseline.unit_cycle_days == Decimal("25.0")
    assert result["groups_processed"] == 1
    assert result["total_orders"] == 3


@pytest.mark.asyncio
async def test_single_sample_can_promote_baseline(db_session):
    db_session.add(
        ProductionOrderHistorySrc(
            production_order_no="PO-SINGLE-001",
            material_no="PART-SINGLE-001",
            material_desc="平衡缸MC1-25.1-13",
            machine_model="MC1-80",
            plant="1000",
            start_time_actual=datetime(2026, 1, 1),
            finish_time_actual=datetime(2026, 1, 11),
            production_qty=Decimal("1"),
            order_status="已完工",
        )
    )
    await db_session.commit()

    service = PartCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    repo = PartCycleBaselineRepo(db_session)
    baseline = await repo.find_by_model_and_part_type("MC1-80", "平衡缸", "1000")

    assert baseline is not None
    assert baseline.sample_count == 1
    assert baseline.cycle_source == "history"
    assert result["groups_processed"] == 1
    assert result["promoted_groups"] == 1
    assert result["skipped_low_sample"] == 0


@pytest.mark.asyncio
async def test_skips_non_completed_orders(db_session):
    db_session.add(
        ProductionOrderHistorySrc(
            production_order_no="PO003",
            material_no="PART-003",
            material_desc="左导轨总成MC1-25.1-13",
            machine_model="MC1-80",
            start_time_actual=datetime(2026, 1, 1),
            finish_time_actual=datetime(2026, 1, 10),
            production_qty=Decimal("1"),
            order_status="进行中",
        )
    )
    await db_session.commit()

    service = PartCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    assert result["groups_processed"] == 0
    assert result["total_orders"] == 0


@pytest.mark.asyncio
async def test_skips_rows_without_part_type_or_machine_model(db_session):
    db_session.add_all(
        [
            ProductionOrderHistorySrc(
                production_order_no="PO004",
                material_no="PART-004",
                material_desc="PART-004",
                machine_model="MC1-80",
                plant="1000",
                start_time_actual=datetime(2026, 1, 1),
                finish_time_actual=datetime(2026, 1, 10),
                production_qty=Decimal("1"),
                order_status="已完工",
            ),
            ProductionOrderHistorySrc(
                production_order_no="PO005",
                material_no="PART-005",
                material_desc="左导轨总成MC1-25.1-18",
                machine_model=None,
                plant="1000",
                start_time_actual=datetime(2026, 1, 1),
                finish_time_actual=datetime(2026, 1, 10),
                production_qty=Decimal("1"),
                order_status="已完工",
            ),
        ]
    )
    await db_session.commit()

    service = PartCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    repo = PartCycleBaselineRepo(db_session)
    baseline = await repo.find_by_model_and_part_type("MC1-80", "左导轨总成", "1000")

    assert baseline is None
    assert result["groups_processed"] == 0
    assert result["total_orders"] == 2


@pytest.mark.asyncio
async def test_rebuild_normalizes_cycle_precision(db_session):
    db_session.add(
        ProductionOrderHistorySrc(
            production_order_no="PO-PRECISION-001",
            material_no="PART-PRECISION-001",
            material_desc="\u5e73\u8861\u7f38\u603b\u6210MC1-80.1-01",
            machine_model="MC1-80-PRECISION",
            plant="1100",
            start_time_actual=datetime(2026, 1, 1, 0, 0, 0),
            finish_time_actual=datetime(2026, 1, 3, 13, 26, 24),
            production_qty=Decimal("2"),
            order_status="\u5df2\u5b8c\u5de5",
        )
    )
    await db_session.commit()

    service = PartCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    repo = PartCycleBaselineRepo(db_session)
    baseline = await repo.find_by_model_and_part_type("MC1-80-PRECISION", "\u5e73\u8861\u7f38\u603b\u6210", "1100")

    assert baseline is not None
    assert baseline.cycle_days == Decimal("3")
    assert baseline.unit_cycle_days == Decimal("1.3")
    assert result["groups_processed"] == 1
