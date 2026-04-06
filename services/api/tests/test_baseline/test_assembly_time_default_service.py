from decimal import Decimal

import pytest

from app.baseline.assembly_time_default_service import AssemblyTimeDefaultService
from app.repository.assembly_time_repo import AssemblyTimeRepo


@pytest.mark.asyncio
async def test_ensure_default_sub_assembly(db_session):
    service = AssemblyTimeDefaultService(db_session)
    record = await service.ensure_default(
        machine_model="MC1-80",
        product_series="MC1",
        assembly_name="机身",
        is_final_assembly=False,
    )
    await db_session.commit()

    assert record is not None
    assert record.assembly_time_days == Decimal("1")
    assert record.is_default is True
    assert record.production_sequence == 1


@pytest.mark.asyncio
async def test_ensure_default_final_assembly(db_session):
    service = AssemblyTimeDefaultService(db_session)
    record = await service.ensure_default(
        machine_model="MC1-80",
        product_series="MC1",
        assembly_name="整机总装",
        is_final_assembly=True,
    )
    await db_session.commit()

    assert record is not None
    assert record.assembly_time_days == Decimal("3")
    assert record.is_final_assembly is True
    assert record.production_sequence == 1


@pytest.mark.asyncio
async def test_ensure_default_final_assembly_sequence_follows_last_sub_assembly(db_session):
    service = AssemblyTimeDefaultService(db_session)
    await service.ensure_default("MC1-80", "MC1", "机身", False)
    await service.ensure_default("MC1-80", "MC1", "电气", False)
    await db_session.commit()

    repo = AssemblyTimeRepo(db_session)
    electric = await repo.find_by_model_and_assembly("MC1-80", "电气")
    electric.production_sequence = 7
    await db_session.commit()

    final_record = await service.ensure_default("MC1-80", "MC1", "整机总装", True)
    await db_session.commit()

    assert final_record.production_sequence == 8


@pytest.mark.asyncio
async def test_does_not_overwrite_existing(db_session):
    service = AssemblyTimeDefaultService(db_session)
    await service.ensure_default("MC1-80", "MC1", "机身", False)
    await db_session.commit()

    repo = AssemblyTimeRepo(db_session)
    existing = await repo.find_by_model_and_assembly("MC1-80", "机身")
    existing.assembly_time_days = Decimal("5")
    existing.is_default = False
    await db_session.commit()

    record = await service.ensure_default("MC1-80", "MC1", "机身", False)
    await db_session.commit()

    assert record.assembly_time_days == Decimal("5")
    assert record.is_default is False


@pytest.mark.asyncio
async def test_default_sequence_mapping(db_session):
    service = AssemblyTimeDefaultService(db_session)

    await service.ensure_default("MC1-80", "MC1", "传动", False)
    await service.ensure_default("MC1-80", "MC1", "滑块", False)
    await service.ensure_default("MC1-80", "MC1", "电气", False)
    await service.ensure_default("MC1-80", "MC1", "离合器", False)
    await db_session.commit()

    repo = AssemblyTimeRepo(db_session)
    transmission = await repo.find_by_model_and_assembly("MC1-80", "传动")
    assert transmission.production_sequence == 2
    slider = await repo.find_by_model_and_assembly("MC1-80", "滑块")
    assert slider.production_sequence == 2
    electric = await repo.find_by_model_and_assembly("MC1-80", "电气")
    assert electric.production_sequence == 5
    clutch = await repo.find_by_model_and_assembly("MC1-80", "离合器")
    assert clutch.production_sequence == 3


@pytest.mark.asyncio
async def test_ensure_sub_assembly_defaults_reconciles_existing_final_assembly_sequence(db_session):
    service = AssemblyTimeDefaultService(db_session)
    final_record = await service.ensure_default(
        machine_model="MC1-81",
        product_series="MC1",
        assembly_name="整机总装",
        is_final_assembly=True,
    )
    await db_session.commit()

    assert final_record.production_sequence == 1

    await service.ensure_sub_assembly_defaults(
        machine_model="MC1-81",
        product_series="MC1",
        assembly_names=["机身", "电气"],
    )
    await db_session.commit()

    repo = AssemblyTimeRepo(db_session)
    refreshed_final = await repo.find_by_model_and_assembly("MC1-81", "整机总装")
    assert refreshed_final is not None
    assert refreshed_final.production_sequence == 6
