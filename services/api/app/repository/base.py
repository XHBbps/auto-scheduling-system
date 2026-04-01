from typing import TypeVar, Generic, Type, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model_class: Type[ModelT]):
        self.session = session
        self.model_class = model_class

    async def get_by_id(self, id_: int) -> ModelT | None:
        return await self.session.get(self.model_class, id_)

    async def list_all(self) -> Sequence[ModelT]:
        result = await self.session.execute(select(self.model_class))
        return result.scalars().all()

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def add_all(self, entities: list[ModelT]) -> list[ModelT]:
        self.session.add_all(entities)
        await self.session.flush()
        return entities

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(self.model_class)
        )
        return result.scalar_one()

    async def exists_any(self) -> bool:
        result = await self.session.execute(select(self.model_class).limit(1))
        return result.scalar_one_or_none() is not None

    async def commit(self) -> None:
        await self.session.commit()
