import pytest

from app.models.bom_relation import BomRelationSrc
from app.scheduler.assembly_identify_service import AssemblyIdentifyService


@pytest.mark.asyncio
async def test_identify_assemblies(db_session):
    bom_rows = [
        BomRelationSrc(
            machine_material_no="MACH001", plant="1000",
            material_no="MACH001",
            bom_component_no="COMP001", bom_component_desc="机身体总成MC1-80",
            bom_level=1, is_self_made=False, is_top_level=True, part_type="虚拟件",
        ),
        BomRelationSrc(
            machine_material_no="MACH001", plant="1000",
            material_no="MACH001",
            bom_component_no="COMP002", bom_component_desc="飞轮MC1-80",
            bom_level=1, is_self_made=False, is_top_level=True, part_type="虚拟件",
        ),
        BomRelationSrc(
            machine_material_no="MACH001", plant="1000",
            material_no="MACH001",
            bom_component_no="COMP003", bom_component_desc="润滑MC1-80",
            bom_level=1, is_self_made=False, is_top_level=True, part_type="虚拟件",
        ),
        BomRelationSrc(
            machine_material_no="MACH001", plant="1000",
            material_no="MACH001",
            bom_component_no="COMP004", bom_component_desc="平垫圈MC1-80",
            bom_level=1, is_self_made=True, is_top_level=True, part_type="自产件",
        ),
        BomRelationSrc(
            machine_material_no="MACH001", plant="1000",
            material_no="COMP001",
            bom_component_no="COMP001-CHILD", bom_component_desc="机身体焊接件MC1-80",
            bom_level=2, is_self_made=True, is_top_level=False, part_type="自产件",
        ),
    ]
    for r in bom_rows:
        db_session.add(r)
    await db_session.commit()

    service = AssemblyIdentifyService(db_session)
    assemblies = await service.identify(
        machine_material_no="MACH001",
        machine_model="MC1-80",
        product_series="MC1",
    )

    names = [a["assembly_name"] for a in assemblies]
    assert "机身" in names
    assert "传动" in names
    assert "润滑" not in names
    assert "机身体焊接件" not in names


@pytest.mark.asyncio
async def test_empty_bom(db_session):
    service = AssemblyIdentifyService(db_session)
    assemblies = await service.identify(
        machine_material_no="NONEXIST",
        machine_model="MC1-80",
        product_series="MC1",
    )
    assert assemblies == []
