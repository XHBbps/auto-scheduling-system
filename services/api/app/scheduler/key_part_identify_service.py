import logging
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.text_parse_utils import extract_part_type
from app.models.part_cycle_baseline import PartCycleBaseline
from app.repository.bom_relation_repo import BomRelationRepo
from app.models.bom_relation import BomRelationSrc
from app.repository.part_cycle_baseline_repo import PartCycleBaselineRepo

logger = logging.getLogger(__name__)

_DEFAULT_PART_CYCLE_DAYS = Decimal("1")


class KeyPartIdentifyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.bom_repo = BomRelationRepo(session)
        self.baseline_repo = PartCycleBaselineRepo(session)

    async def list_self_made_parts(
        self,
        machine_material_no: str,
        assembly_bom_component_no: str,
        plant: str | None,
    ) -> list[BomRelationSrc]:
        """List direct self-made children under an assembly."""
        rows = await self.bom_repo.find_self_made_children_for_assemblies(
            machine_material_no=machine_material_no,
            assembly_component_nos=[assembly_bom_component_no],
            plant=plant,
        )
        return list(rows)

    @staticmethod
    def _build_bom_children_index(rows: Sequence[BomRelationSrc]) -> dict[str, list[BomRelationSrc]]:
        grouped: dict[str, list[BomRelationSrc]] = {}
        for row in rows:
            parent_material_no = (row.material_no or "").strip()
            if not parent_material_no:
                continue
            grouped.setdefault(parent_material_no, []).append(row)
        for children in grouped.values():
            children.sort(
                key=lambda item: (
                    item.bom_level if item.bom_level is not None else 0,
                    item.bom_component_no or "",
                    item.id,
                )
            )
        return grouped

    def _collect_recursive_self_made_parts_from_rows(
        self,
        *,
        assembly_bom_component_no: str,
        assembly_name: str,
        rows: Sequence[BomRelationSrc],
    ) -> list[dict[str, Any]]:
        children_index = self._build_bom_children_index(rows)
        results: list[dict[str, Any]] = []

        root_label = assembly_name or assembly_bom_component_no or "-"
        root_no = assembly_bom_component_no or "-"
        root_segment = f"{root_label}({root_no})"

        def walk(
            parent_material_no: str,
            parent_name: str,
            depth: int,
            path_segments: list[str],
            path_key_segments: list[str],
            visited_materials: set[str],
        ) -> None:
            for child in children_index.get(parent_material_no, []):
                child_material_no = (child.bom_component_no or "").strip()
                child_name = (child.bom_component_desc or "").strip() or child_material_no or "-"
                if not child_material_no:
                    continue
                if child_material_no in visited_materials:
                    logger.warning(
                        "Skip recursive part traversal cycle for assembly %s, material %s",
                        assembly_bom_component_no,
                        child_material_no,
                    )
                    continue

                next_path_segments = [*path_segments, f"{child_name}({child_material_no})"]
                next_path_key_segments = [
                    *path_key_segments,
                    str(child.id or f"{parent_material_no}->{child_material_no}"),
                ]
                next_visited_materials = { *visited_materials, child_material_no }

                if child.is_self_made:
                    results.append({
                        "row": child,
                        "parent_material_no": parent_material_no or None,
                        "parent_name": parent_name or None,
                        "node_level": depth,
                        "bom_path": " / ".join(next_path_segments),
                        "bom_path_key": ">".join(next_path_key_segments),
                    })

                walk(
                    child_material_no,
                    child_name,
                    depth + 1,
                    next_path_segments,
                    next_path_key_segments,
                    next_visited_materials,
                )

        walk(
            assembly_bom_component_no,
            assembly_name,
            1,
            [root_segment],
            [f"root:{assembly_bom_component_no}"],
            {assembly_bom_component_no},
        )
        return results

    async def list_recursive_self_made_parts(
        self,
        machine_material_no: str,
        assembly_bom_component_no: str,
        *,
        plant: str | None,
        assembly_name: str,
        bom_rows: Sequence[BomRelationSrc] | None = None,
    ) -> list[dict[str, Any]]:
        rows = list(bom_rows) if bom_rows is not None else list(
            await self.bom_repo.find_by_machine(machine_material_no, plant)
        )
        return self._collect_recursive_self_made_parts_from_rows(
            assembly_bom_component_no=assembly_bom_component_no,
            assembly_name=assembly_name,
            rows=rows,
        )

    async def list_recursive_self_made_parts_for_assemblies(
        self,
        machine_material_no: str,
        plant: str | None,
        assemblies: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        if not assemblies:
            return {}
        rows = await self.bom_repo.find_by_machine(machine_material_no, plant)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for assembly in assemblies:
            assembly_component_no = (assembly.get("bom_component_no") or "").strip()
            if not assembly_component_no:
                continue
            grouped[assembly_component_no] = self._collect_recursive_self_made_parts_from_rows(
                assembly_bom_component_no=assembly_component_no,
                assembly_name=assembly.get("assembly_name") or assembly_component_no,
                rows=rows,
            )
        return grouped

    async def list_self_made_parts_for_assemblies(
        self,
        machine_material_no: str,
        plant: str | None,
        assembly_bom_component_nos: list[str],
    ) -> dict[str, list[BomRelationSrc]]:
        rows = await self.bom_repo.find_self_made_children_for_assemblies(
            machine_material_no=machine_material_no,
            assembly_component_nos=assembly_bom_component_nos,
            plant=plant,
        )
        grouped: dict[str, list[BomRelationSrc]] = {}
        for row in rows:
            grouped.setdefault(row.material_no, []).append(row)
        return grouped

    async def build_cycle_lookup(self, machine_model: str, plant: str | None = None) -> dict[str, Any]:
        baselines = await self.baseline_repo.list_active_by_model(machine_model, plant)
        exact_map: dict[str, PartCycleBaseline] = {}
        for baseline in baselines:
            part_type = (baseline.core_part_name or baseline.material_no or "").strip()
            if part_type and part_type not in exact_map:
                exact_map[part_type] = baseline
        return {
            "machine_model": machine_model,
            "plant": plant,
            "exact_map": exact_map,
            "baselines": list(baselines),
        }

    @staticmethod
    def _match_part_cycle_from_lookup(
        material_no: str,
        desc: str | None,
        lookup: dict[str, Any] | None,
    ) -> tuple[Decimal, bool, str]:
        part_type = extract_part_type(desc or "")
        if lookup:
            exact_map = lookup.get("exact_map") or {}
            baseline = exact_map.get(part_type)
            if baseline:
                return baseline.cycle_days, False, "part_type_exact"

            if part_type:
                for item in lookup.get("baselines") or []:
                    baseline_part_type = (item.core_part_name or item.material_no or "").strip()
                    material_desc = item.material_desc or ""
                    if baseline_part_type == part_type or material_desc.startswith(part_type):
                        return item.cycle_days, False, "part_type_prefix"

        return _DEFAULT_PART_CYCLE_DAYS, True, "default"

    def identify_from_children(
        self,
        children: list[BomRelationSrc],
        machine_model: str,
        cycle_lookup: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not children:
            return None

        best: dict[str, Any] | None = None
        best_cycle = Decimal("-1")

        for child in children:
            cycle, is_default, match_rule = self._match_part_cycle_from_lookup(
                child.bom_component_no,
                child.bom_component_desc,
                cycle_lookup,
            )
            if cycle > best_cycle:
                best_cycle = cycle
                best = {
                    "key_part_material_no": child.bom_component_no,
                    "key_part_name": child.bom_component_desc,
                    "key_part_raw_material_desc": child.bom_component_desc,
                    "key_part_cycle_days": cycle,
                    "is_default": is_default,
                    "match_rule": match_rule,
                }

        return best

    def identify_from_recursive_nodes(
        self,
        nodes: list[dict[str, Any]],
        machine_model: str,
        cycle_lookup: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not nodes:
            return None

        best: dict[str, Any] | None = None
        best_cycle = Decimal("-1")

        for node in nodes:
            row: BomRelationSrc | None = node.get("row")
            if row is None:
                continue
            cycle, is_default, match_rule = self._match_part_cycle_from_lookup(
                row.bom_component_no or "",
                row.bom_component_desc,
                cycle_lookup,
            )
            if cycle > best_cycle:
                best_cycle = cycle
                best = {
                    "key_part_material_no": row.bom_component_no,
                    "key_part_name": row.bom_component_desc,
                    "key_part_raw_material_desc": row.bom_component_desc,
                    "key_part_cycle_days": cycle,
                    "is_default": is_default,
                    "match_rule": match_rule,
                    "bom_path": node.get("bom_path"),
                    "bom_path_key": node.get("bom_path_key"),
                    "parent_material_no": node.get("parent_material_no"),
                    "parent_name": node.get("parent_name"),
                    "node_level": node.get("node_level"),
                }

        return best

    async def identify(
        self,
        machine_material_no: str,
        assembly_bom_component_no: str,
        plant: str | None = None,
        machine_model: str = "",
    ) -> dict[str, Any] | None:
        """Find the key self-made part (longest cycle) for an assembly."""
        children = await self.list_self_made_parts(
            machine_material_no=machine_material_no,
            assembly_bom_component_no=assembly_bom_component_no,
            plant=plant,
        )
        cycle_lookup = await self.build_cycle_lookup(machine_model, plant)
        return self.identify_from_children(children, machine_model, cycle_lookup)

    async def get_part_cycle(
        self,
        material_no: str,
        machine_model: str,
        desc: str | None,
        plant: str | None = None,
        cycle_lookup: dict[str, Any] | None = None,
    ) -> tuple[Decimal, bool, str]:
        """Get part cycle days. Returns (days, is_default, match_rule)."""
        if cycle_lookup:
            return self._match_part_cycle_from_lookup(material_no, desc, cycle_lookup)

        part_type = extract_part_type(desc or "")
        if part_type:
            baseline = await self.baseline_repo.find_by_model_and_part_type(
                machine_model, part_type, plant
            )
            if baseline:
                return baseline.cycle_days, False, "part_type_exact"

            baseline = await self.baseline_repo.find_by_model_and_desc_prefix(
                machine_model, part_type, plant
            )
            if baseline:
                return baseline.cycle_days, False, "part_type_prefix"

        return _DEFAULT_PART_CYCLE_DAYS, True, "default"
