import argparse
import asyncio
import json
import logging
from collections import defaultdict

from sqlalchemy import select

from app.common.plant_utils import normalize_plant
from app.database import async_session_factory
from app.models.bom_relation import BomRelationSrc
from app.sync.bom_sync_service import _compute_bom_levels

logger = logging.getLogger(__name__)


async def backfill_bom_levels(
    *,
    dry_run: bool,
    machine_material_no: str | None = None,
    plant: str | None = None,
) -> dict[str, int | str | None]:
    async with async_session_factory() as session:
        stmt = select(BomRelationSrc).order_by(
            BomRelationSrc.machine_material_no.asc(),
            BomRelationSrc.plant.asc(),
            BomRelationSrc.id.asc(),
        )
        if machine_material_no:
            stmt = stmt.where(BomRelationSrc.machine_material_no == machine_material_no)

        rows = list((await session.execute(stmt)).scalars().all())
        normalized_plant = normalize_plant(plant) if plant is not None else None
        grouped: dict[tuple[str, str], list[BomRelationSrc]] = defaultdict(list)
        for row in rows:
            row_plant = normalize_plant(row.plant)
            if normalized_plant is not None and row_plant != normalized_plant:
                continue
            grouped[(row.machine_material_no, row_plant)].append(row)

        groups_processed = 0
        rows_scanned = 0
        rows_updated = 0

        for (current_machine_material_no, _current_plant), group_rows in grouped.items():
            groups_processed += 1
            rows_scanned += len(group_rows)
            payload_rows: list[dict[str, object]] = []
            for row in group_rows:
                payload_rows.append(
                    {
                        "material_no": row.material_no,
                        "bom_component_no": row.bom_component_no,
                        "bom_level": row.bom_level,
                        "is_top_level": row.is_top_level,
                        "__row__": row,
                    }
                )

            _compute_bom_levels(payload_rows, current_machine_material_no)

            for payload in payload_rows:
                orm_row: BomRelationSrc = payload["__row__"]  # type: ignore[assignment]
                new_bom_level = payload["bom_level"]
                new_is_top_level = payload["is_top_level"]
                if orm_row.bom_level == new_bom_level and orm_row.is_top_level == new_is_top_level:
                    continue
                orm_row.bom_level = new_bom_level  # type: ignore[assignment]
                orm_row.is_top_level = new_is_top_level  # type: ignore[assignment]
                rows_updated += 1

        result = {
            "dry_run": dry_run,
            "machine_material_no": machine_material_no,
            "plant": normalized_plant,
            "groups_processed": groups_processed,
            "rows_scanned": rows_scanned,
            "rows_updated": rows_updated,
        }

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

        return result


async def run(dry_run: bool, machine_material_no: str | None, plant: str | None) -> None:
    result = await backfill_bom_levels(
        dry_run=dry_run,
        machine_material_no=machine_material_no,
        plant=plant,
    )
    logger.info("BOM level backfill finished: %s", json.dumps(result, ensure_ascii=False, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Recompute stored BOM levels from existing parent-child rows.")
    parser.add_argument("--dry-run", action="store_true", help="Only calculate the changes without committing them.")
    parser.add_argument("--machine-material-no", help="Only backfill a single machine material number.")
    parser.add_argument("--plant", help="Only backfill one plant after normalization.")
    args = parser.parse_args()

    from app.common.logging_setup import configure_logging

    configure_logging()
    asyncio.run(
        run(
            dry_run=args.dry_run,
            machine_material_no=args.machine_material_no,
            plant=args.plant,
        )
    )


if __name__ == "__main__":
    main()
