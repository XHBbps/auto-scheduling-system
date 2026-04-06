import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.calendar_utils import subtract_workdays
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.part_schedule_result import PartScheduleResult
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.part_schedule_result_repo import PartScheduleResultRepo
from app.repository.work_calendar_repo import WorkCalendarRepo
from app.scheduler.assembly_identify_service import AssemblyIdentifyService
from app.scheduler.key_part_identify_service import KeyPartIdentifyService

logger = logging.getLogger(__name__)


class PartScheduleService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.assembly_service = AssemblyIdentifyService(session)
        self.key_part_service = KeyPartIdentifyService(session)
        self.result_repo = PartScheduleResultRepo(session)
        self.calendar_repo = WorkCalendarRepo(session)

    async def build(
        self,
        order_line_id: int,
        machine_schedule_id: int,
    ) -> list[PartScheduleResult]:
        """Build part schedules for all assemblies of an order."""
        order = await self.session.get(SalesPlanOrderLineSrc, order_line_id)
        msr = await self.session.get(MachineScheduleResult, machine_schedule_id)
        if not order or not msr:
            return []
        self._ensure_machine_schedule_matches_order(order_line_id, msr)

        # Identify assemblies
        assemblies = await self.assembly_service.identify(
            machine_material_no=order.material_no or "",
            plant=order.delivery_plant,
            machine_model=order.product_model or "",
            product_series=order.product_series,
        )

        if not assemblies:
            return []

        # Machine end date
        machine_end = msr.planned_end_date
        machine_end_date = machine_end.date() if isinstance(machine_end, datetime) else machine_end

        # Load calendar
        start_range = machine_end_date - timedelta(days=365)
        end_range = machine_end_date + timedelta(days=30)
        calendar = await self.calendar_repo.get_calendar_map(start_range, end_range)
        recursive_self_made_parts_map = await self.key_part_service.list_recursive_self_made_parts_for_assemblies(
            machine_material_no=order.material_no or "",
            plant=order.delivery_plant,
            assemblies=assemblies,
        )
        cycle_lookup = await self.key_part_service.build_cycle_lookup(
            order.product_model or "",
            order.delivery_plant,
        )

        # Delete existing part results
        await self.result_repo.delete_by_order_line_id(order_line_id)

        # Group by production_sequence
        seq_groups: dict[int, list[dict]] = {}
        for asm in assemblies:
            seq = asm["production_sequence"]
            seq_groups.setdefault(seq, []).append(asm)

        sorted_seqs = sorted(seq_groups.keys(), reverse=True)  # highest seq first

        # Walk backward from machine end date
        current_end_date = machine_end_date
        # First subtract final assembly time
        final_asm_days = int(msr.machine_assembly_days or 3)
        current_end_date = subtract_workdays(current_end_date, final_asm_days, calendar)

        results = []
        for seq in sorted_seqs:
            group = seq_groups[seq]
            group_end_date = current_end_date

            max_assembly_time = Decimal("0")
            for asm in group:
                recursive_self_made_parts = list(recursive_self_made_parts_map.get(asm["bom_component_no"], []))

                # Find key part
                key_part = self.key_part_service.identify_from_recursive_nodes(
                    recursive_self_made_parts,
                    machine_model=order.product_model or "",
                    cycle_lookup=cycle_lookup,
                )

                part_end = group_end_date
                part_start = part_end
                key_part_cycle = Decimal("0")
                key_part_data: dict[str, Any] = {}
                is_default_part = False
                match_rule = ""

                if key_part:
                    key_part_cycle = key_part["key_part_cycle_days"]
                    part_start = subtract_workdays(part_end, int(key_part_cycle), calendar)
                    key_part_data = key_part
                    is_default_part = key_part["is_default"]
                    match_rule = key_part["match_rule"]

                asm_time = asm["assembly_time_days"]
                if asm_time > max_assembly_time:
                    max_assembly_time = asm_time

                default_flags = {}
                if asm["is_default_time"]:
                    default_flags["assembly_time"] = True
                if is_default_part:
                    default_flags["key_part_cycle"] = True

                part_rows = recursive_self_made_parts or [None]
                for part_node in part_rows:
                    row_default_flags = dict(default_flags)
                    part_cycle_days = None
                    part_cycle_is_default = False
                    part_cycle_match_rule = None
                    row = part_node.get("row") if part_node else None
                    if row:
                        (
                            part_cycle_days,
                            part_cycle_is_default,
                            part_cycle_match_rule,
                        ) = await self.key_part_service.get_part_cycle(
                            row.bom_component_no,
                            order.product_model or "",
                            row.bom_component_desc,
                            plant=order.delivery_plant,
                            cycle_lookup=cycle_lookup,
                        )
                        if part_cycle_is_default:
                            row_default_flags["part_cycle"] = True

                    entity = PartScheduleResult(
                        order_line_id=order_line_id,
                        machine_schedule_id=machine_schedule_id,
                        assembly_name=asm["assembly_name"],
                        production_sequence=asm["production_sequence"],
                        assembly_time_days=asm_time,
                        assembly_is_default=asm["is_default_time"],
                        parent_material_no=part_node.get("parent_material_no") if part_node else None,
                        parent_name=part_node.get("parent_name") if part_node else None,
                        node_level=part_node.get("node_level") if part_node else None,
                        bom_path=part_node.get("bom_path") if part_node else None,
                        bom_path_key=part_node.get("bom_path_key") if part_node else None,
                        part_material_no=row.bom_component_no if row else None,
                        part_name=row.bom_component_desc if row else None,
                        part_raw_material_desc=row.bom_component_desc if row else None,
                        is_key_part=(
                            bool(part_node) and part_node.get("bom_path_key") == key_part_data.get("bom_path_key")
                        ),
                        part_cycle_days=part_cycle_days,
                        part_cycle_is_default=part_cycle_is_default,
                        part_cycle_match_rule=part_cycle_match_rule,
                        key_part_material_no=key_part_data.get("key_part_material_no"),
                        key_part_name=key_part_data.get("key_part_name"),
                        key_part_raw_material_desc=key_part_data.get("key_part_raw_material_desc"),
                        key_part_cycle_days=key_part_cycle if key_part else None,
                        key_part_is_default=is_default_part,
                        cycle_match_rule=match_rule,
                        planned_start_date=datetime.combine(part_start, datetime.min.time()) if key_part else None,
                        planned_end_date=datetime.combine(part_end, datetime.min.time()),
                        warning_level="normal",
                        default_flags=row_default_flags if row_default_flags else None,
                    )
                    self.session.add(entity)
                    results.append(entity)

            # Move end date backward by the max assembly time in this group
            current_end_date = subtract_workdays(current_end_date, int(max_assembly_time), calendar)

        await self.session.flush()
        return results

    @staticmethod
    def _ensure_machine_schedule_matches_order(
        order_line_id: int,
        machine_schedule: MachineScheduleResult,
    ) -> None:
        if machine_schedule.order_line_id != order_line_id:
            raise ValueError("machine schedule result does not belong to the requested order_line_id")
