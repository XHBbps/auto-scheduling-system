import logging

from sqlalchemy import desc, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.models.sales_plan import SalesPlanOrderLineSrc

logger = logging.getLogger(__name__)


class DrawingStatusSyncService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def refresh_all(self) -> int:
        return len(await self.refresh_all_with_ids())

    async def refresh_all_with_ids(self) -> list[int]:
        stmt = select(SalesPlanOrderLineSrc).where(SalesPlanOrderLineSrc.drawing_released == False)
        result = await self.session.execute(stmt)
        orders = result.scalars().all()
        return await self._refresh_orders(orders)

    async def refresh_by_order_ids(self, order_ids: list[int]) -> int:
        return len(await self.refresh_by_order_ids_with_ids(order_ids))

    async def refresh_by_order_ids_with_ids(self, order_ids: list[int]) -> list[int]:
        stmt = select(SalesPlanOrderLineSrc).where(SalesPlanOrderLineSrc.id.in_(order_ids))
        result = await self.session.execute(stmt)
        orders = result.scalars().all()
        return await self._refresh_orders(orders)

    async def _refresh_orders(self, orders: list[SalesPlanOrderLineSrc]) -> list[int]:
        detail_matches = await self._load_research_by_detail_ids(
            [order.detail_id for order in orders if order.detail_id]
        )
        pair_matches = await self._load_research_by_order_material_pairs(
            [(order.order_no, order.material_no) for order in orders if order.order_no and order.material_no]
        )
        updated_ids: list[int] = []
        for order in orders:
            if self._try_backfill(
                order,
                detail_matches=detail_matches,
                pair_matches=pair_matches,
            ):
                updated_ids.append(order.id)

        await self.session.flush()
        return updated_ids

    async def _load_research_by_detail_ids(
        self,
        detail_ids: list[str],
    ) -> dict[str, MachineCycleHistorySrc]:
        unique_detail_ids = list(dict.fromkeys(detail_ids))
        if not unique_detail_ids:
            return {}
        stmt = select(MachineCycleHistorySrc).where(
            MachineCycleHistorySrc.detail_id.in_(unique_detail_ids),
            MachineCycleHistorySrc.drawing_release_date.is_not(None),
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return {row.detail_id: row for row in rows}

    async def _load_research_by_order_material_pairs(
        self,
        pairs: list[tuple[str, str]],
    ) -> dict[tuple[str, str], MachineCycleHistorySrc]:
        unique_pairs = list(dict.fromkeys((str(order_no), str(material_no)) for order_no, material_no in pairs))
        if not unique_pairs:
            return {}
        stmt = (
            select(MachineCycleHistorySrc)
            .where(
                tuple_(
                    MachineCycleHistorySrc.order_no,
                    MachineCycleHistorySrc.machine_material_no,
                ).in_(unique_pairs),
                MachineCycleHistorySrc.drawing_release_date.is_not(None),
            )
            .order_by(
                desc(MachineCycleHistorySrc.drawing_release_date),
                desc(MachineCycleHistorySrc.id),
            )
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        pair_matches: dict[tuple[str, str], MachineCycleHistorySrc] = {}
        for row in rows:
            key = (row.order_no, row.machine_material_no)
            if key not in pair_matches:
                pair_matches[key] = row
        return pair_matches

    @staticmethod
    def _try_backfill(
        order: SalesPlanOrderLineSrc,
        *,
        detail_matches: dict[str, MachineCycleHistorySrc],
        pair_matches: dict[tuple[str, str], MachineCycleHistorySrc],
    ) -> bool:
        research = detail_matches.get(order.detail_id) if order.detail_id else None
        if research is None and order.order_no and order.material_no:
            research = pair_matches.get((order.order_no, order.material_no))
        if research and research.drawing_release_date:
            order.drawing_released = True
            order.drawing_release_date = research.drawing_release_date
            return True

        return False
