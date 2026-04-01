from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.assembly_time import AssemblyTimeBaseline
from app.models.bom_relation import BomRelationSrc
from app.models.data_issue import DataIssueRecord
from app.models.part_cycle_baseline import PartCycleBaseline
from app.models.part_schedule_result import PartScheduleResult
from app.services.historical_text_backfill_service import HistoricalTextBackfillService


def _to_mojibake(value: str) -> str:
    return value.encode("utf-8").decode("gb18030")


@pytest.mark.asyncio
async def test_historical_text_backfill_service_updates_dirty_fields(db_session):
    issue = DataIssueRecord(
        issue_type=_to_mojibake("整机周期缺失"),
        issue_title=_to_mojibake("整机周期缺失"),
        issue_detail=f"{_to_mojibake('整机周期缺失')}?product_model=MC1-80?已按默认周期?",
        status="open",
    )
    bom = BomRelationSrc(
        machine_material_no="M1",
        machine_material_desc=_to_mojibake("整机"),
        material_no="C1",
        material_desc=_to_mojibake("机身"),
        bom_component_no="B1",
        bom_component_desc=_to_mojibake("机身总成"),
        part_type=_to_mojibake("外购"),
        component_qty=Decimal("1"),
        bom_level=1,
        is_self_made=True,
    )
    part = PartScheduleResult(
        order_line_id=1,
        assembly_name=_to_mojibake("机身"),
        production_sequence=1,
        assembly_time_days=Decimal("1"),
        part_material_no="P1",
        part_name=_to_mojibake("零件"),
        part_raw_material_desc=_to_mojibake("机身总成"),
        is_key_part=False,
        warning_level="normal",
    )
    assembly = AssemblyTimeBaseline(
        machine_model="MC1-80",
        assembly_name=_to_mojibake("整机总装"),
        assembly_time_days=Decimal("3"),
        is_final_assembly=True,
        production_sequence=99,
    )
    part_cycle = PartCycleBaseline(
        material_no="P1",
        material_desc=_to_mojibake("机身"),
        core_part_name=_to_mojibake("机身"),
        machine_model="MC1-80",
        plant="1000",
        ref_batch_qty=Decimal("1"),
        cycle_days=Decimal("2"),
        unit_cycle_days=Decimal("2"),
        is_active=True,
    )
    db_session.add_all([issue, bom, part, assembly, part_cycle])
    await db_session.commit()

    result = await HistoricalTextBackfillService(db_session).backfill()

    assert result["updated_rows"] >= 5
    assert result["tables"]["data_issue_record"]["field_update_counts"]["issue_detail"] == 1

    stored_issue = (await db_session.execute(select(DataIssueRecord))).scalars().one()
    stored_bom = (await db_session.execute(select(BomRelationSrc))).scalars().one()
    stored_part = (await db_session.execute(select(PartScheduleResult))).scalars().one()
    stored_assembly = (await db_session.execute(select(AssemblyTimeBaseline))).scalars().one()
    stored_part_cycle = (await db_session.execute(select(PartCycleBaseline))).scalars().one()

    assert stored_issue.issue_type == "整机周期缺失"
    assert stored_issue.issue_detail == "整机周期缺失；product_model=MC1-80；已按默认周期。"
    assert stored_bom.machine_material_desc == "整机"
    assert stored_bom.material_desc == "机身"
    assert stored_bom.part_type == "外购"
    assert stored_part.assembly_name == "机身"
    assert stored_part.part_name == "零件"
    assert stored_assembly.assembly_name == "整机总装"
    assert stored_part_cycle.core_part_name == "机身"


@pytest.mark.asyncio
async def test_historical_text_backfill_service_dry_run_does_not_commit(db_session):
    issue = DataIssueRecord(
        issue_type=_to_mojibake("整机周期缺失"),
        issue_title=_to_mojibake("整机周期缺失"),
        issue_detail=_to_mojibake("整机周期缺失"),
        status="open",
    )
    db_session.add(issue)
    await db_session.commit()

    result = await HistoricalTextBackfillService(db_session).backfill(dry_run=True)

    assert result["dry_run"] is True

    stored_issue = (await db_session.execute(select(DataIssueRecord))).scalars().one()
    assert stored_issue.issue_type == _to_mojibake("整机周期缺失")
