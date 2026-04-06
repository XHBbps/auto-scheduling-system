from collections.abc import Sequence

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assembly_time import AssemblyTimeBaseline
from app.repository.base import BaseRepository

FINAL_ASSEMBLY_NAME = "整机总装"


class AssemblyTimeRepo(BaseRepository[AssemblyTimeBaseline]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AssemblyTimeBaseline)

    async def find_by_model_and_assembly(self, machine_model: str, assembly_name: str) -> AssemblyTimeBaseline | None:
        stmt = select(AssemblyTimeBaseline).where(
            and_(
                AssemblyTimeBaseline.machine_model == machine_model,
                AssemblyTimeBaseline.assembly_name == assembly_name,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_final_assembly(self, machine_model: str) -> AssemblyTimeBaseline | None:
        stmt = (
            select(AssemblyTimeBaseline)
            .where(
                and_(
                    AssemblyTimeBaseline.machine_model == machine_model,
                    or_(
                        AssemblyTimeBaseline.is_final_assembly.is_(True),
                        AssemblyTimeBaseline.assembly_name == FINAL_ASSEMBLY_NAME,
                    ),
                )
            )
            .order_by(
                AssemblyTimeBaseline.is_final_assembly.desc(),
                AssemblyTimeBaseline.id.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all_by_model(self, machine_model: str) -> Sequence[AssemblyTimeBaseline]:
        stmt = (
            select(AssemblyTimeBaseline)
            .where(AssemblyTimeBaseline.machine_model == machine_model)
            .order_by(AssemblyTimeBaseline.production_sequence)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_max_sub_assembly_sequence(self, machine_model: str) -> int | None:
        stmt = select(func.max(AssemblyTimeBaseline.production_sequence)).where(
            and_(
                AssemblyTimeBaseline.machine_model == machine_model,
                AssemblyTimeBaseline.is_final_assembly.is_(False),
                AssemblyTimeBaseline.assembly_name != FINAL_ASSEMBLY_NAME,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
