import logging
from collections.abc import Iterable
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assembly_time import AssemblyTimeBaseline
from app.repository.assembly_time_repo import AssemblyTimeRepo

logger = logging.getLogger(__name__)

_DEFAULT_SUB_ASSEMBLY_DAYS = Decimal("1")
_DEFAULT_FINAL_ASSEMBLY_DAYS = Decimal("3")
_FINAL_ASSEMBLY_NAME = "整机总装"

_DEFAULT_SEQUENCE_MAP = {
    "机身": 1,
    "传动": 2,
    "滑块": 2,
    "平衡缸": 3,
    "空气管路": 4,
    "电气": 5,
}
_DEFAULT_SEQUENCE_FALLBACK = 3


class AssemblyTimeDefaultService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AssemblyTimeRepo(session)

    async def ensure_default(
        self,
        machine_model: str,
        product_series: str | None,
        assembly_name: str,
        is_final_assembly: bool,
    ) -> AssemblyTimeBaseline:
        """Return existing record or create a default one."""
        existing = await self.repo.find_by_model_and_assembly(machine_model, assembly_name)
        if existing:
            return existing

        days = _DEFAULT_FINAL_ASSEMBLY_DAYS if is_final_assembly else _DEFAULT_SUB_ASSEMBLY_DAYS
        sequence = await self._resolve_default_sequence(
            machine_model=machine_model,
            assembly_name=assembly_name,
            is_final_assembly=is_final_assembly,
        )

        entity = AssemblyTimeBaseline(
            machine_model=machine_model,
            product_series=product_series,
            assembly_name=assembly_name,
            assembly_time_days=days,
            is_final_assembly=is_final_assembly,
            production_sequence=sequence,
            is_default=True,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def ensure_sub_assembly_defaults(
        self,
        machine_model: str,
        product_series: str | None,
        assembly_names: Iterable[str],
    ) -> dict[str, AssemblyTimeBaseline]:
        normalized_names: list[str] = []
        seen_names: set[str] = set()
        for assembly_name in assembly_names:
            if not assembly_name or assembly_name in seen_names:
                continue
            seen_names.add(assembly_name)
            normalized_names.append(assembly_name)

        if not normalized_names:
            return {}

        existing_map = {
            item.assembly_name: item for item in await self.repo.find_all_by_model(machine_model) if item.assembly_name
        }
        result_map: dict[str, AssemblyTimeBaseline] = {
            name: existing_map[name] for name in normalized_names if name in existing_map
        }

        for assembly_name in normalized_names:
            if assembly_name in result_map:
                continue
            entity = AssemblyTimeBaseline(
                machine_model=machine_model,
                product_series=product_series,
                assembly_name=assembly_name,
                assembly_time_days=_DEFAULT_SUB_ASSEMBLY_DAYS,
                is_final_assembly=False,
                production_sequence=_DEFAULT_SEQUENCE_MAP.get(
                    assembly_name,
                    _DEFAULT_SEQUENCE_FALLBACK,
                ),
                is_default=True,
            )
            self.session.add(entity)
            result_map[assembly_name] = entity

        if len(result_map) != len(normalized_names):
            logger.warning("Assembly default ensure produced mismatched result set for %s", machine_model)
        await self.session.flush()
        await self.reconcile_final_assembly_sequence(machine_model)
        return result_map

    async def reconcile_final_assembly_sequence(self, machine_model: str) -> AssemblyTimeBaseline | None:
        final_record = await self.repo.find_final_assembly(machine_model)
        if not final_record:
            return None

        final_record.is_final_assembly = True
        final_record.production_sequence = await self._resolve_default_sequence(
            machine_model=machine_model,
            assembly_name=final_record.assembly_name,
            is_final_assembly=True,
        )
        await self.session.flush()
        return final_record

    async def _resolve_default_sequence(
        self,
        machine_model: str,
        assembly_name: str,
        is_final_assembly: bool,
    ) -> int:
        if self._is_whole_machine_final_assembly(assembly_name, is_final_assembly):
            max_sequence = await self.repo.find_max_sub_assembly_sequence(machine_model)
            return (max_sequence or 0) + 1

        return _DEFAULT_SEQUENCE_MAP.get(assembly_name, _DEFAULT_SEQUENCE_FALLBACK)

    @staticmethod
    def _is_whole_machine_final_assembly(assembly_name: str, is_final_assembly: bool) -> bool:
        return is_final_assembly and (assembly_name or "").strip() == _FINAL_ASSEMBLY_NAME
