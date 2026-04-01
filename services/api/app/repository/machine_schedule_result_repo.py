from datetime import datetime, timedelta
from typing import Any, Sequence
from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_schedule_result import MachineScheduleResult
from app.repository.base import BaseRepository


class MachineScheduleResultRepo(BaseRepository[MachineScheduleResult]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MachineScheduleResult)

    @staticmethod
    def _parse_date_start(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def _parse_date_end(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            return None

    async def upsert_by_order_line_id(
        self, order_line_id: int, data: dict[str, Any]
    ) -> MachineScheduleResult:
        stmt = select(MachineScheduleResult).where(
            MachineScheduleResult.order_line_id == order_line_id
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            await self.session.flush()
            return existing
        entity = MachineScheduleResult(order_line_id=order_line_id, **data)
        return await self.add(entity)

    async def find_by_order_line_id(self, order_line_id: int) -> MachineScheduleResult | None:
        stmt = select(MachineScheduleResult).where(
            MachineScheduleResult.order_line_id == order_line_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_order_line_ids(
        self,
        order_line_ids: Sequence[int],
    ) -> Sequence[MachineScheduleResult]:
        if not order_line_ids:
            return []
        stmt = select(MachineScheduleResult).where(
            MachineScheduleResult.order_line_id.in_(order_line_ids)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_order_line_id(self, order_line_id: int) -> int:
        stmt = delete(MachineScheduleResult).where(
            MachineScheduleResult.order_line_id == order_line_id
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def paginate(
        self, page_no: int = 1, page_size: int = 20, **filters: Any
    ) -> tuple[Sequence[MachineScheduleResult], int]:
        base = select(MachineScheduleResult)
        count_base = select(func.count()).select_from(MachineScheduleResult)

        conditions = []
        if filters.get("order_line_id") is not None:
            conditions.append(MachineScheduleResult.order_line_id == filters["order_line_id"])
        if filters.get("contract_no"):
            conditions.append(MachineScheduleResult.contract_no.ilike(f"%{filters['contract_no']}%"))
        if filters.get("customer_name"):
            conditions.append(MachineScheduleResult.customer_name.ilike(f"%{filters['customer_name']}%"))
        if filters.get("product_series"):
            conditions.append(MachineScheduleResult.product_series == filters["product_series"])
        if filters.get("product_model"):
            conditions.append(MachineScheduleResult.product_model.ilike(f"%{filters['product_model']}%"))
        if filters.get("order_no"):
            conditions.append(MachineScheduleResult.order_no.ilike(f"%{filters['order_no']}%"))
        if filters.get("schedule_status"):
            conditions.append(MachineScheduleResult.schedule_status == filters["schedule_status"])
        if filters.get("warning_level"):
            conditions.append(MachineScheduleResult.warning_level == filters["warning_level"])
        if filters.get("drawing_released") is not None:
            conditions.append(MachineScheduleResult.drawing_released == filters["drawing_released"])
        date_from = self._parse_date_start(filters.get("date_from"))
        date_to = self._parse_date_end(filters.get("date_to"))
        if date_from:
            conditions.append(MachineScheduleResult.confirmed_delivery_date >= date_from)
        if date_to:
            conditions.append(MachineScheduleResult.confirmed_delivery_date < date_to)

        if conditions:
            base = base.where(and_(*conditions))
            count_base = count_base.where(and_(*conditions))

        total = (await self.session.execute(count_base)).scalar_one()
        stmt = base.order_by(MachineScheduleResult.id.desc()).offset(
            (page_no - 1) * page_size
        ).limit(page_size)
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total
