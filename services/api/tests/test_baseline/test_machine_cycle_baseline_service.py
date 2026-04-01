import pytest
from decimal import Decimal

from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.baseline.machine_cycle_baseline_service import MachineCycleBaselineService
from app.repository.machine_cycle_baseline_repo import MachineCycleBaselineRepo


@pytest.mark.asyncio
async def test_build_baseline_single_group(db_session):
    for i, days in enumerate([Decimal("60"), Decimal("80"), Decimal("70")]):
        db_session.add(MachineCycleHistorySrc(
            detail_id=f"DT00{i}",
            machine_model="MC1-80",
            product_series="MC1",
            order_qty=Decimal("1"),
            cycle_days=days,
        ))
    await db_session.commit()

    service = MachineCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    repo = MachineCycleBaselineRepo(db_session)
    baseline = await repo.find_by_model_and_qty("MC1-80", Decimal("1"))
    assert baseline is not None
    assert baseline.cycle_days_median == Decimal("70")  # median of 60, 70, 80
    assert baseline.sample_count == 3
    assert result["groups_processed"] == 1


@pytest.mark.asyncio
async def test_build_baseline_multiple_groups(db_session):
    for i, days in enumerate([Decimal("60"), Decimal("80")]):
        db_session.add(MachineCycleHistorySrc(
            detail_id=f"G1-{i}", machine_model="MC1-80",
            product_series="MC1", order_qty=Decimal("1"), cycle_days=days,
        ))
    db_session.add(MachineCycleHistorySrc(
        detail_id="G2-0", machine_model="MC1-80",
        product_series="MC1", order_qty=Decimal("2"), cycle_days=Decimal("100"),
    ))
    await db_session.commit()

    service = MachineCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    repo = MachineCycleBaselineRepo(db_session)
    b1 = await repo.find_by_model_and_qty("MC1-80", Decimal("1"))
    b2 = await repo.find_by_model_and_qty("MC1-80", Decimal("2"))
    assert b1 is not None
    assert b1.cycle_days_median == Decimal("70")
    assert b2 is not None
    assert b2.cycle_days_median == Decimal("100")
    assert result["groups_processed"] == 2


@pytest.mark.asyncio
async def test_build_baseline_skips_null_cycle(db_session):
    db_session.add(MachineCycleHistorySrc(
        detail_id="DT-NULL", machine_model="MC1-80",
        product_series="MC1", order_qty=Decimal("1"), cycle_days=None,
    ))
    await db_session.commit()

    service = MachineCycleBaselineService(db_session)
    result = await service.rebuild()
    await db_session.commit()

    repo = MachineCycleBaselineRepo(db_session)
    baseline = await repo.find_by_model_and_qty("MC1-80", Decimal("1"))
    assert baseline is None
    assert result["groups_processed"] == 0


@pytest.mark.asyncio
async def test_rebuild_deduplicates_active_baselines_for_same_model_and_qty(db_session):
    db_session.add_all([
        MachineCycleBaseline(
            product_series="旧系列",
            machine_model="MC2-200",
            order_qty=Decimal("1"),
            cycle_days_median=Decimal("60"),
            sample_count=1,
            is_active=True,
            remark="旧记录",
        ),
        MachineCycleBaseline(
            product_series="开式压力机",
            machine_model="MC2-200",
            order_qty=Decimal("1"),
            cycle_days_median=Decimal("51"),
            sample_count=18,
            is_active=True,
        ),
        MachineCycleHistorySrc(
            detail_id="MC2-200-1",
            machine_model="MC2-200",
            product_series="开式压力机",
            order_qty=Decimal("1"),
            cycle_days=Decimal("50"),
        ),
        MachineCycleHistorySrc(
            detail_id="MC2-200-2",
            machine_model="MC2-200",
            product_series="开式压力机",
            order_qty=Decimal("1"),
            cycle_days=Decimal("52"),
        ),
    ])
    await db_session.commit()

    service = MachineCycleBaselineService(db_session)
    await service.rebuild()
    await db_session.commit()

    repo = MachineCycleBaselineRepo(db_session)
    baseline = await repo.find_by_model_and_qty("MC2-200", Decimal("1"))
    all_rows = await repo.find_all_by_model("MC2-200")

    assert baseline is not None
    assert baseline.product_series == "开式压力机"
    assert baseline.cycle_days_median == Decimal("51.0")
    assert baseline.is_active is True
    assert len(all_rows) == 1
