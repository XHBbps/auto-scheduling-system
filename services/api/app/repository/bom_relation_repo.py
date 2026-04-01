from typing import Sequence
from sqlalchemy import select, delete, and_, func, literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.plant_utils import normalize_plant
from app.models.bom_relation import BomRelationSrc
from app.repository.base import BaseRepository


class BomRelationRepo(BaseRepository[BomRelationSrc]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, BomRelationSrc)

    @staticmethod
    def _normalized_plant_expr():
        return func.coalesce(BomRelationSrc.plant, literal(normalize_plant(None)))

    async def delete_by_machine_and_plant(self, machine_material_no: str, plant: str) -> int:
        stmt = delete(BomRelationSrc).where(
            and_(
                BomRelationSrc.machine_material_no == machine_material_no,
                self._normalized_plant_expr() == normalize_plant(plant),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def find_by_machine(self, machine_material_no: str, plant: str | None = None) -> Sequence[BomRelationSrc]:
        conditions = [BomRelationSrc.machine_material_no == machine_material_no]
        if plant is not None:
            conditions.append(self._normalized_plant_expr() == normalize_plant(plant))
        stmt = select(BomRelationSrc).where(*conditions).order_by(BomRelationSrc.bom_level)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_direct_children(self, machine_material_no: str, plant: str | None = None) -> Sequence[BomRelationSrc]:
        conditions = [
            BomRelationSrc.machine_material_no == machine_material_no,
            BomRelationSrc.material_no == machine_material_no,
        ]
        if plant is not None:
            conditions.append(self._normalized_plant_expr() == normalize_plant(plant))
        stmt = select(BomRelationSrc).where(and_(*conditions))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_self_made_children_for_assemblies(
        self,
        machine_material_no: str,
        assembly_component_nos: Sequence[str],
        plant: str | None = None,
    ) -> Sequence[BomRelationSrc]:
        if not assembly_component_nos:
            return []
        conditions = [
            BomRelationSrc.machine_material_no == machine_material_no,
            BomRelationSrc.material_no.in_(assembly_component_nos),
            BomRelationSrc.is_self_made == True,
        ]
        if plant is not None:
            conditions.append(self._normalized_plant_expr() == normalize_plant(plant))
        stmt = select(BomRelationSrc).where(and_(*conditions)).order_by(
            BomRelationSrc.material_no.asc(),
            BomRelationSrc.bom_component_no.asc(),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def has_machine_bom(self, machine_material_no: str, plant: str | None = None) -> bool:
        conditions = [BomRelationSrc.machine_material_no == machine_material_no]
        if plant is not None:
            conditions.append(self._normalized_plant_expr() == normalize_plant(plant))
        stmt = select(func.count()).select_from(BomRelationSrc).where(*conditions)
        count = (await self.session.execute(stmt)).scalar_one()
        return count > 0
