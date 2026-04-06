from collections import defaultdict
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dirty_text_utils import cleanup_issue_detail, repair_mojibake_text
from app.models.assembly_time import AssemblyTimeBaseline
from app.models.bom_relation import BomRelationSrc
from app.models.data_issue import DataIssueRecord
from app.models.part_cycle_baseline import PartCycleBaseline
from app.models.part_schedule_result import PartScheduleResult


class HistoricalTextBackfillService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def backfill(self, dry_run: bool = False) -> dict:
        summary = {
            "dry_run": dry_run,
            "tables": {},
            "updated_rows": 0,
            "updated_fields": 0,
        }

        for table_name, result in [
            await self._backfill_model(
                DataIssueRecord,
                {
                    "issue_type": repair_mojibake_text,
                    "issue_title": repair_mojibake_text,
                    "issue_detail": cleanup_issue_detail,
                    "remark": repair_mojibake_text,
                },
            ),
            await self._backfill_model(
                BomRelationSrc,
                {
                    "machine_material_desc": repair_mojibake_text,
                    "material_desc": repair_mojibake_text,
                    "bom_component_desc": repair_mojibake_text,
                    "part_type": repair_mojibake_text,
                },
            ),
            await self._backfill_model(
                PartScheduleResult,
                {
                    "assembly_name": repair_mojibake_text,
                    "part_name": repair_mojibake_text,
                    "part_raw_material_desc": repair_mojibake_text,
                    "key_part_name": repair_mojibake_text,
                    "key_part_raw_material_desc": repair_mojibake_text,
                    "remark": repair_mojibake_text,
                },
            ),
            await self._backfill_model(
                AssemblyTimeBaseline,
                {
                    "assembly_name": repair_mojibake_text,
                    "remark": repair_mojibake_text,
                },
            ),
            await self._backfill_model(
                PartCycleBaseline,
                {
                    "material_desc": repair_mojibake_text,
                    "core_part_name": repair_mojibake_text,
                    "remark": repair_mojibake_text,
                },
            ),
        ]:
            summary["tables"][table_name] = result
            summary["updated_rows"] += result["updated_rows"]
            summary["updated_fields"] += result["updated_fields"]

        if not dry_run:
            await self.session.commit()
        else:
            await self.session.rollback()

        return summary

    async def _backfill_model(
        self,
        model,
        field_cleaners: dict[str, Callable[[str | None], str | None]],
    ) -> tuple[str, dict]:
        rows = (await self.session.execute(select(model))).scalars().all()
        updated_rows = 0
        updated_fields = 0
        field_update_counts = defaultdict(int)

        for row in rows:
            row_changed = False
            for field_name, cleaner in field_cleaners.items():
                old_value = getattr(row, field_name, None)
                new_value = cleaner(old_value)
                if new_value != old_value:
                    setattr(row, field_name, new_value)
                    row_changed = True
                    updated_fields += 1
                    field_update_counts[field_name] += 1
            if row_changed:
                updated_rows += 1

        await self.session.flush()
        return model.__tablename__, {
            "updated_rows": updated_rows,
            "updated_fields": updated_fields,
            "field_update_counts": dict(field_update_counts),
        }
