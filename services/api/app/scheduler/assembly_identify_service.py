import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.baseline.assembly_time_default_service import AssemblyTimeDefaultService
from app.common.text_parse_utils import normalize_assembly_name
from app.repository.bom_relation_repo import BomRelationRepo

logger = logging.getLogger(__name__)


class AssemblyIdentifyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.bom_repo = BomRelationRepo(session)
        self.assembly_default = AssemblyTimeDefaultService(session)

    async def identify(
        self,
        machine_material_no: str,
        plant: str | None = None,
        machine_model: str = "",
        product_series: str | None = None,
    ) -> list[dict[str, Any]]:
        """Identify assemblies from machine direct-child self-made BOM items."""
        direct_children = await self.bom_repo.find_direct_children(machine_material_no, plant)

        seen_names: set[str] = set()
        assembly_rows: list[tuple[str, Any]] = []

        for bom_row in direct_children:
            name = normalize_assembly_name(bom_row.bom_component_desc or "")
            if not name:
                continue
            if name in seen_names:
                continue
            seen_names.add(name)
            assembly_rows.append((name, bom_row))

        if not assembly_rows:
            return []

        assembly_time_map = await self.assembly_default.ensure_sub_assembly_defaults(
            machine_model=machine_model,
            product_series=product_series,
            assembly_names=[name for name, _ in assembly_rows],
        )

        assemblies = []
        for name, bom_row in assembly_rows:
            at_record = assembly_time_map[name]
            assemblies.append(
                {
                    "assembly_name": name,
                    "production_sequence": at_record.production_sequence,
                    "assembly_time_days": at_record.assembly_time_days,
                    "is_default_time": at_record.is_default,
                    "bom_component_no": bom_row.bom_component_no,
                    "bom_component_desc": bom_row.bom_component_desc,
                }
            )

        # Sort by production_sequence
        assemblies.sort(key=lambda a: a["production_sequence"])
        return assemblies
