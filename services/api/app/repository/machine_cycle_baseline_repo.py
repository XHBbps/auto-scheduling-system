from typing import Any, Sequence
from decimal import Decimal
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.repository.base import BaseRepository


class MachineCycleBaselineRepo(BaseRepository[MachineCycleBaseline]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MachineCycleBaseline)

    @staticmethod
    def _ordered_stmt(*conditions):
        return (
            select(MachineCycleBaseline)
            .where(and_(*conditions))
            .order_by(
                MachineCycleBaseline.is_active.desc(),
                MachineCycleBaseline.sample_count.desc(),
                MachineCycleBaseline.updated_at.desc(),
                MachineCycleBaseline.id.desc(),
            )
        )

    async def find_by_model_and_qty(
        self, machine_model: str, order_qty: Decimal
    ) -> MachineCycleBaseline | None:
        stmt = self._ordered_stmt(
            MachineCycleBaseline.machine_model == machine_model,
            MachineCycleBaseline.order_qty == order_qty,
            MachineCycleBaseline.is_active == True,
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all_by_model(self, machine_model: str) -> Sequence[MachineCycleBaseline]:
        stmt = self._ordered_stmt(
            MachineCycleBaseline.machine_model == machine_model,
            MachineCycleBaseline.is_active == True,
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        deduped: dict[Decimal, MachineCycleBaseline] = {}
        for row in rows:
            deduped.setdefault(row.order_qty, row)
        return [deduped[qty] for qty in sorted(deduped.keys())]

    async def deactivate_duplicate_active_rows(self) -> int:
        stmt = self._ordered_stmt(MachineCycleBaseline.is_active == True)
        rows = (await self.session.execute(stmt)).scalars().all()
        keep_map: dict[tuple[str, Decimal], MachineCycleBaseline] = {}
        updated = 0
        for row in rows:
            key = (row.machine_model, row.order_qty)
            if key not in keep_map:
                keep_map[key] = row
                continue
            if row.is_active:
                row.is_active = False
                row.remark = "自动停用：存在同机型同数量的更优基准记录"
                updated += 1
        if updated:
            await self.session.flush()
        return updated

    async def upsert_baseline(
        self, product_series: str, machine_model: str, order_qty: Decimal,
        data: dict[str, Any],
    ) -> MachineCycleBaseline:
        stmt = self._ordered_stmt(
            MachineCycleBaseline.machine_model == machine_model,
            MachineCycleBaseline.order_qty == order_qty,
        )
        rows = (await self.session.execute(stmt)).scalars().all()

        target = None
        for row in rows:
            if (row.product_series or "") == product_series:
                target = row
                break
        if target is None and rows:
            target = rows[0]

        if target:
            target.product_series = product_series
            for k, v in data.items():
                setattr(target, k, v)
            target.is_active = True
            for duplicate in rows:
                if duplicate.id != target.id and duplicate.is_active:
                    duplicate.is_active = False
                    duplicate.remark = "自动停用：存在同机型同数量的主基准记录"
            await self.session.flush()
            return target

        entity = MachineCycleBaseline(
            product_series=product_series,
            machine_model=machine_model,
            order_qty=order_qty,
            **data,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity
