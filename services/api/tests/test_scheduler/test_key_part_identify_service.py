import pytest
from decimal import Decimal

from app.models.bom_relation import BomRelationSrc
from app.models.part_cycle_baseline import PartCycleBaseline
from app.scheduler.key_part_identify_service import KeyPartIdentifyService


@pytest.mark.asyncio
async def test_selects_longest_cycle_part_by_part_type(db_session):
    db_session.add_all(
        [
            BomRelationSrc(
                machine_material_no="MACH001",
                plant="1000",
                material_no="ASM001",
                bom_component_no="PART_A",
                bom_component_desc="右导轨总成MC1-25.1-13",
                bom_level=3,
                is_self_made=True,
                part_type="自产",
            ),
            BomRelationSrc(
                machine_material_no="MACH001",
                plant="1000",
                material_no="ASM001",
                bom_component_no="PART_B",
                bom_component_desc="左导轨总成MC1-25.1-13",
                bom_level=3,
                is_self_made=True,
                part_type="自产",
            ),
            PartCycleBaseline(
                material_no="右导轨总成",
                material_desc="右导轨总成MC1-25.1-13",
                core_part_name="右导轨总成",
                machine_model="MC1-80",
                ref_batch_qty=Decimal("1"),
                cycle_days=Decimal("10"),
                unit_cycle_days=Decimal("10"),
                match_rule="part_type_exact",
                is_active=True,
            ),
            PartCycleBaseline(
                material_no="左导轨总成",
                material_desc="左导轨总成MC1-25.1-13",
                core_part_name="左导轨总成",
                machine_model="MC1-80",
                ref_batch_qty=Decimal("1"),
                cycle_days=Decimal("20"),
                unit_cycle_days=Decimal("20"),
                match_rule="part_type_exact",
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    service = KeyPartIdentifyService(db_session)
    result = await service.identify(
        machine_material_no="MACH001",
        assembly_bom_component_no="ASM001",
        machine_model="MC1-80",
    )

    assert result is not None
    assert result["key_part_material_no"] == "PART_B"
    assert result["key_part_cycle_days"] == Decimal("20")
    assert result["is_default"] is False
    assert result["match_rule"] == "part_type_exact"


@pytest.mark.asyncio
async def test_identify_from_children_with_prefetched_lookup(db_session):
    child_a = BomRelationSrc(
        machine_material_no="MACH001",
        plant="1000",
        material_no="ASM002",
        bom_component_no="PART_X",
        bom_component_desc="右导轨总成MC1-25.1-13",
        bom_level=3,
        is_self_made=True,
        part_type="自产",
    )
    child_b = BomRelationSrc(
        machine_material_no="MACH001",
        plant="1000",
        material_no="ASM002",
        bom_component_no="PART_Y",
        bom_component_desc="左导轨总成MC1-25.1-13",
        bom_level=3,
        is_self_made=True,
        part_type="自产",
    )
    db_session.add_all(
        [
            child_a,
            child_b,
            PartCycleBaseline(
                material_no="右导轨总成",
                material_desc="右导轨总成MC1-25.1-13",
                core_part_name="右导轨总成",
                machine_model="MC1-80",
                ref_batch_qty=Decimal("1"),
                cycle_days=Decimal("8"),
                unit_cycle_days=Decimal("8"),
                match_rule="part_type_exact",
                is_active=True,
            ),
            PartCycleBaseline(
                material_no="左导轨总成",
                material_desc="左导轨总成MC1-25.1-13",
                core_part_name="左导轨总成",
                machine_model="MC1-80",
                ref_batch_qty=Decimal("1"),
                cycle_days=Decimal("18"),
                unit_cycle_days=Decimal("18"),
                match_rule="part_type_exact",
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    service = KeyPartIdentifyService(db_session)
    lookup = await service.build_cycle_lookup("MC1-80")
    result = service.identify_from_children([child_a, child_b], "MC1-80", lookup)

    assert result is not None
    assert result["key_part_material_no"] == "PART_Y"
    assert result["key_part_cycle_days"] == Decimal("18")
    assert result["match_rule"] == "part_type_exact"


@pytest.mark.asyncio
async def test_get_part_cycle_falls_back_to_desc_prefix(db_session):
    db_session.add(
        PartCycleBaseline(
            material_no="旧零件编码",
            material_desc="右导轨总成历史版本",
            core_part_name="旧零件编码",
            machine_model="MC1-80",
            ref_batch_qty=Decimal("1"),
            cycle_days=Decimal("12"),
            unit_cycle_days=Decimal("12"),
            match_rule="legacy_prefix",
            is_active=True,
        )
    )
    await db_session.commit()

    service = KeyPartIdentifyService(db_session)
    cycle_days, is_default, match_rule = await service.get_part_cycle(
        material_no="PART_Z",
        machine_model="MC1-80",
        desc="右导轨总成MC1-25.1-99",
    )

    assert cycle_days == Decimal("12")
    assert is_default is False
    assert match_rule == "part_type_prefix"


@pytest.mark.asyncio
async def test_default_when_no_baseline(db_session):
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH001",
            plant="1000",
            material_no="ASM003",
            bom_component_no="PART_C",
            bom_component_desc="丝杆防护罩组件",
            bom_level=3,
            is_self_made=True,
            part_type="自产",
        )
    )
    await db_session.commit()

    service = KeyPartIdentifyService(db_session)
    result = await service.identify(
        machine_material_no="MACH001",
        assembly_bom_component_no="ASM003",
        machine_model="MC1-80",
    )

    assert result is not None
    assert result["key_part_cycle_days"] == Decimal("1")
    assert result["is_default"] is True
    assert result["match_rule"] == "default"


@pytest.mark.asyncio
async def test_no_self_made_children(db_session):
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH001",
            plant="1000",
            material_no="ASM004",
            bom_component_no="PURCH_A",
            bom_component_desc="标准件螺栓",
            bom_level=3,
            is_self_made=False,
            part_type="外购",
        )
    )
    await db_session.commit()

    service = KeyPartIdentifyService(db_session)
    result = await service.identify(
        machine_material_no="MACH001",
        assembly_bom_component_no="ASM004",
        machine_model="MC1-80",
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_part_cycle_prefers_plant_specific_baseline_then_falls_back(db_session):
    db_session.add_all(
        [
            PartCycleBaseline(
                material_no="右导轨总成",
                material_desc="右导轨总成通用版",
                core_part_name="右导轨总成",
                machine_model="MC1-80",
                plant=None,
                ref_batch_qty=Decimal("1"),
                cycle_days=Decimal("6"),
                unit_cycle_days=Decimal("6"),
                match_rule="part_type_exact",
                cycle_source="manual",
                is_active=True,
            ),
            PartCycleBaseline(
                material_no="右导轨总成",
                material_desc="右导轨总成1000工厂版",
                core_part_name="右导轨总成",
                machine_model="MC1-80",
                plant="1000",
                ref_batch_qty=Decimal("1"),
                cycle_days=Decimal("9"),
                unit_cycle_days=Decimal("9"),
                match_rule="part_type_exact_with_plant",
                cycle_source="manual",
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    service = KeyPartIdentifyService(db_session)

    cycle_days, is_default, match_rule = await service.get_part_cycle(
        material_no="PART_Z",
        machine_model="MC1-80",
        desc="右导轨总成MC1-25.1-99",
        plant="1000",
    )
    assert cycle_days == Decimal("9")
    assert is_default is False
    assert match_rule == "part_type_exact"

    cycle_days, is_default, match_rule = await service.get_part_cycle(
        material_no="PART_Z",
        machine_model="MC1-80",
        desc="右导轨总成MC1-25.1-99",
        plant="2000",
    )
    assert cycle_days == Decimal("6")
    assert is_default is False
    assert match_rule == "part_type_exact"
