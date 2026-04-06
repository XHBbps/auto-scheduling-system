from collections.abc import AsyncIterator, Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, case, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ScheduleStatus
from app.common.query_sort_utils import build_sort_expression, resolve_order_by
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.repository.base import BaseRepository
from app.repository.order_schedule_snapshot_aggregate_helper import OrderScheduleSnapshotAggregateHelper
from app.repository.order_schedule_snapshot_calendar_helper import OrderScheduleSnapshotCalendarHelper


class OrderScheduleSnapshotRepo(BaseRepository[OrderScheduleSnapshot]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, OrderScheduleSnapshot)
        self.aggregate_helper = OrderScheduleSnapshotAggregateHelper(session)
        self.calendar_helper = OrderScheduleSnapshotCalendarHelper(session)

    async def _normalize_snapshot_data(
        self,
        *,
        order_line_id: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = dict(data)
        schedule_status = normalized.get("schedule_status")
        machine_schedule_id = normalized.get("machine_schedule_id")
        if schedule_status not in {ScheduleStatus.SCHEDULED, ScheduleStatus.SCHEDULED_STALE}:
            normalized["machine_schedule_id"] = None
            machine_schedule_id = None
        if machine_schedule_id is None:
            return normalized

        machine_schedule = await self.session.get(MachineScheduleResult, machine_schedule_id)
        if machine_schedule and machine_schedule.order_line_id != order_line_id:
            raise ValueError("machine schedule result does not belong to the requested order_line_id")
        return normalized

    @staticmethod
    def _allowed_sort_fields() -> dict[str, Any]:
        return {
            "order_line_id": OrderScheduleSnapshot.order_line_id,
            "contract_no": OrderScheduleSnapshot.contract_no,
            "customer_name": OrderScheduleSnapshot.customer_name,
            "product_series": OrderScheduleSnapshot.product_series,
            "product_model": OrderScheduleSnapshot.product_model,
            "product_name": OrderScheduleSnapshot.product_name,
            "material_no": OrderScheduleSnapshot.material_no,
            "plant": OrderScheduleSnapshot.plant,
            "quantity": OrderScheduleSnapshot.quantity,
            "order_type": OrderScheduleSnapshot.order_type,
            "line_total_amount": OrderScheduleSnapshot.line_total_amount,
            "order_date": OrderScheduleSnapshot.order_date,
            "business_group": OrderScheduleSnapshot.business_group,
            "custom_no": OrderScheduleSnapshot.custom_no,
            "sales_person_name": OrderScheduleSnapshot.sales_person_name,
            "sales_branch_company": OrderScheduleSnapshot.sales_branch_company,
            "sales_sub_branch": OrderScheduleSnapshot.sales_sub_branch,
            "confirmed_delivery_date": OrderScheduleSnapshot.confirmed_delivery_date,
            "order_no": OrderScheduleSnapshot.order_no,
            "sap_code": OrderScheduleSnapshot.sap_code,
            "sap_line_no": OrderScheduleSnapshot.sap_line_no,
            "custom_requirement": OrderScheduleSnapshot.custom_requirement,
            "review_comment": OrderScheduleSnapshot.review_comment,
            "drawing_released": OrderScheduleSnapshot.drawing_released,
            "schedule_status": OrderScheduleSnapshot.schedule_status,
            "planned_start_date": OrderScheduleSnapshot.planned_start_date,
            "planned_end_date": OrderScheduleSnapshot.planned_end_date,
            "warning_level": OrderScheduleSnapshot.warning_level,
        }

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

    async def find_by_order_line_id(self, order_line_id: int) -> OrderScheduleSnapshot | None:
        stmt = select(OrderScheduleSnapshot).where(OrderScheduleSnapshot.order_line_id == order_line_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_order_line_ids(
        self,
        order_line_ids: Sequence[int],
    ) -> Sequence[OrderScheduleSnapshot]:
        if not order_line_ids:
            return []
        stmt = select(OrderScheduleSnapshot).where(OrderScheduleSnapshot.order_line_id.in_(order_line_ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert_by_order_line_id(
        self,
        order_line_id: int,
        data: dict[str, Any],
    ) -> OrderScheduleSnapshot:
        existing = await self.find_by_order_line_id(order_line_id)
        return await self.upsert_loaded_by_order_line_id(
            order_line_id,
            data,
            existing=existing,
        )

    async def upsert_loaded_by_order_line_id(
        self,
        order_line_id: int,
        data: dict[str, Any],
        *,
        existing: OrderScheduleSnapshot | None,
    ) -> OrderScheduleSnapshot:
        normalized = await self._normalize_snapshot_data(
            order_line_id=order_line_id,
            data=data,
        )
        if existing:
            for key, value in normalized.items():
                setattr(existing, key, value)
            await self.session.flush()
            return existing
        entity = OrderScheduleSnapshot(order_line_id=order_line_id, **normalized)
        return await self.add(entity)

    async def delete_by_order_line_id(self, order_line_id: int) -> int:
        stmt = delete(OrderScheduleSnapshot).where(OrderScheduleSnapshot.order_line_id == order_line_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    def _build_conditions(self, filters: dict[str, Any]) -> list[Any]:
        conditions = []
        if filters.get("order_line_id") is not None:
            conditions.append(OrderScheduleSnapshot.order_line_id == filters["order_line_id"])
        if filters.get("contract_no"):
            conditions.append(OrderScheduleSnapshot.contract_no.ilike(f"%{filters['contract_no']}%"))
        if filters.get("customer_name"):
            conditions.append(OrderScheduleSnapshot.customer_name.ilike(f"%{filters['customer_name']}%"))
        if filters.get("product_series"):
            conditions.append(OrderScheduleSnapshot.product_series == filters["product_series"])
        if filters.get("product_model"):
            conditions.append(OrderScheduleSnapshot.product_model.ilike(f"%{filters['product_model']}%"))
        if filters.get("plant"):
            conditions.append(OrderScheduleSnapshot.plant == filters["plant"])
        if filters.get("order_no"):
            conditions.append(OrderScheduleSnapshot.order_no.ilike(f"%{filters['order_no']}%"))
        if filters.get("schedule_status"):
            conditions.append(OrderScheduleSnapshot.schedule_status == filters["schedule_status"])
        if filters.get("warning_level"):
            conditions.append(OrderScheduleSnapshot.warning_level == filters["warning_level"])
        schedule_bucket = filters.get("schedule_bucket")
        if schedule_bucket == "unscheduled":
            conditions.append(OrderScheduleSnapshot.schedule_status != "scheduled")
        elif schedule_bucket == "risk":
            conditions.append(
                or_(
                    OrderScheduleSnapshot.schedule_status != "scheduled",
                    OrderScheduleSnapshot.warning_level == "abnormal",
                )
            )
        if filters.get("drawing_released") is not None:
            conditions.append(OrderScheduleSnapshot.drawing_released == filters["drawing_released"])

        date_from = self._parse_date_start(filters.get("date_from"))
        date_to = self._parse_date_end(filters.get("date_to"))
        if date_from:
            conditions.append(OrderScheduleSnapshot.confirmed_delivery_date >= date_from)
        if date_to:
            conditions.append(OrderScheduleSnapshot.confirmed_delivery_date < date_to)
        return conditions

    def _build_sort_expression(self, sort_field: str | None, sort_order: str | None):
        return build_sort_expression(
            sort_field=sort_field,
            sort_order=sort_order,
            allowed_fields=self._allowed_sort_fields(),
        )

    @staticmethod
    def _default_order_by() -> list[Any]:
        return [
            OrderScheduleSnapshot.confirmed_delivery_date.asc().nullslast(),
            OrderScheduleSnapshot.order_line_id.desc(),
        ]

    async def paginate(
        self,
        page_no: int = 1,
        page_size: int = 20,
        **filters: Any,
    ) -> tuple[Sequence[OrderScheduleSnapshot], int]:
        sort_field = filters.pop("sort_field", None)
        sort_order = filters.pop("sort_order", None)
        base = select(OrderScheduleSnapshot)
        count_base = select(func.count()).select_from(OrderScheduleSnapshot)

        conditions = self._build_conditions(filters)
        if conditions:
            where = and_(*conditions)
            base = base.where(where)
            count_base = count_base.where(where)

        total = (await self.session.execute(count_base)).scalar_one()
        sort_expression = self._build_sort_expression(sort_field, sort_order)
        stmt = (
            base.order_by(
                *resolve_order_by(
                    sort_expression=sort_expression,
                    default_order_by=self._default_order_by(),
                )
            )
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total

    async def list_for_export(self, **filters: Any) -> Sequence[OrderScheduleSnapshot]:
        stmt = self._build_export_stmt(**filters)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_for_export(self, **filters: Any) -> int:
        stmt = select(func.count()).select_from(OrderScheduleSnapshot)
        conditions = self._build_conditions(filters)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def has_export_rows_beyond_limit(
        self,
        *,
        max_rows: int,
        **filters: Any,
    ) -> bool:
        probe_offset = max(int(max_rows), 0)
        stmt = select(OrderScheduleSnapshot.order_line_id)
        conditions = self._build_conditions(filters)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.offset(probe_offset).limit(1)
        return (await self.session.execute(stmt)).first() is not None

    def _build_export_stmt(self, **filters: Any):
        sort_field = filters.pop("sort_field", None)
        sort_order = filters.pop("sort_order", None)
        stmt = select(OrderScheduleSnapshot)
        conditions = self._build_conditions(filters)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(
            *resolve_order_by(
                sort_expression=self._build_sort_expression(sort_field, sort_order),
                default_order_by=self._default_order_by(),
            )
        )
        return stmt

    async def list_for_export_batch(
        self,
        *,
        offset: int,
        limit: int,
        **filters: Any,
    ) -> Sequence[OrderScheduleSnapshot]:
        stmt = self._build_export_stmt(**filters).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def stream_for_export_batches(
        self,
        *,
        batch_size: int,
        **filters: Any,
    ) -> AsyncIterator[list[OrderScheduleSnapshot]]:
        stmt = self._build_export_stmt(**filters).execution_options(
            stream_results=True,
            yield_per=max(int(batch_size), 1),
        )
        result = await self.session.stream_scalars(stmt)
        try:
            async for partition in result.partitions(max(int(batch_size), 1)):
                batch = list(partition)
                if batch:
                    yield batch
        finally:
            await result.close()

    async def list_schedulable_order_line_ids(self) -> list[int]:
        stmt = (
            select(OrderScheduleSnapshot.order_line_id)
            .where(OrderScheduleSnapshot.schedule_status == "schedulable")
            .order_by(
                OrderScheduleSnapshot.confirmed_delivery_date.asc().nullslast(),
                OrderScheduleSnapshot.order_line_id.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_distinct_product_series(self) -> list[str]:
        stmt = (
            select(OrderScheduleSnapshot.product_series)
            .where(OrderScheduleSnapshot.product_series.isnot(None))
            .distinct()
            .order_by(OrderScheduleSnapshot.product_series)
        )
        result = await self.session.execute(stmt)
        return [row for row in result.scalars().all() if row]

    async def get_dashboard_summary(self) -> dict[str, Any]:
        return await self.aggregate_helper.get_dashboard_summary()

    async def summarize_business_groups(self, *, limit: int | None = None) -> list[tuple[str, int, Any]]:
        return await self.aggregate_helper.summarize_business_groups(limit=limit)

    async def count_all(self) -> int:
        return await self.aggregate_helper.count_all()

    async def count_by_schedule_status(self) -> list[tuple[str, int]]:
        return await self.aggregate_helper.count_by_schedule_status()

    async def count_by_warning_level(self) -> list[tuple[str, int]]:
        return await self.aggregate_helper.count_by_warning_level()

    async def count_by_refresh_source(self) -> list[tuple[str, int]]:
        return await self.aggregate_helper.count_by_refresh_source()

    async def get_refresh_bounds(self) -> tuple[datetime | None, datetime | None]:
        return await self.aggregate_helper.get_refresh_bounds()

    async def get_observability_aggregates(self) -> dict[str, Any]:
        return await self.aggregate_helper.get_observability_aggregates()

    @staticmethod
    def _known_order_line_ids_subquery():
        return OrderScheduleSnapshotAggregateHelper.known_order_line_ids_subquery()

    async def list_planned_end_dates(self) -> list[datetime]:
        stmt = select(OrderScheduleSnapshot.planned_end_date).where(OrderScheduleSnapshot.planned_end_date.isnot(None))
        result = await self.session.execute(stmt)
        return [value for value in result.scalars().all() if value]

    async def count_by_planned_end_month(self) -> list[tuple[str, int]]:
        return await self.aggregate_helper.count_by_planned_end_month()

    async def list_warning_orders(self, limit: int = 10) -> Sequence[OrderScheduleSnapshot]:
        stmt = (
            select(OrderScheduleSnapshot)
            .where(
                or_(
                    OrderScheduleSnapshot.warning_level != "normal",
                    OrderScheduleSnapshot.schedule_status != "scheduled",
                )
            )
            .order_by(
                OrderScheduleSnapshot.confirmed_delivery_date.asc().nullslast(),
                OrderScheduleSnapshot.order_line_id.desc(),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_abnormal_orders(self, limit: int = 50) -> Sequence[OrderScheduleSnapshot]:
        stmt = (
            select(OrderScheduleSnapshot)
            .where(OrderScheduleSnapshot.warning_level == "abnormal")
            .order_by(
                OrderScheduleSnapshot.confirmed_delivery_date.asc().nullslast(),
                OrderScheduleSnapshot.order_line_id.asc(),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    def _date_window(start_date: date, end_date: date) -> tuple[datetime, datetime]:
        return OrderScheduleSnapshotCalendarHelper.date_window(start_date, end_date)

    async def count_by_date_field_window(
        self,
        field_name: str,
        start_date: date,
        end_date: date,
        *,
        schedule_bucket: str | None = None,
        warning_level: str | None = None,
    ) -> int:
        return await self.calendar_helper.count_by_date_field_window(
            field_name,
            start_date,
            end_date,
            schedule_bucket=schedule_bucket,
            warning_level=warning_level,
        )

    async def summarize_date_field_window(
        self,
        field_name: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, int]:
        return await self.calendar_helper.summarize_date_field_window(
            field_name,
            start_date,
            end_date,
        )

    async def summarize_date_field_windows(
        self,
        field_name: str,
        windows: Sequence[tuple[str, date, date]],
    ) -> dict[str, dict[str, int]]:
        return await self.calendar_helper.summarize_date_field_windows(
            field_name,
            windows,
        )

    async def list_delivery_risk_orders(
        self,
        start_date: date,
        end_date: date,
        *,
        limit: int = 20,
    ) -> Sequence[OrderScheduleSnapshot]:
        start_dt, end_dt = self._date_window(start_date, end_date)
        stmt = (
            select(OrderScheduleSnapshot)
            .where(
                and_(
                    OrderScheduleSnapshot.confirmed_delivery_date.isnot(None),
                    OrderScheduleSnapshot.confirmed_delivery_date >= start_dt,
                    OrderScheduleSnapshot.confirmed_delivery_date < end_dt,
                    or_(
                        OrderScheduleSnapshot.schedule_status != "scheduled",
                        OrderScheduleSnapshot.warning_level == "abnormal",
                    ),
                )
            )
            .order_by(
                OrderScheduleSnapshot.confirmed_delivery_date.asc().nullslast(),
                case((OrderScheduleSnapshot.warning_level == "abnormal", 0), else_=1).asc(),
                case((OrderScheduleSnapshot.schedule_status != "scheduled", 0), else_=1).asc(),
                OrderScheduleSnapshot.order_line_id.asc(),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    def _day_range(target_date: date) -> tuple[datetime, datetime]:
        return OrderScheduleSnapshotCalendarHelper.day_range(target_date)

    @staticmethod
    def _normalize_decimal(value: Any) -> Decimal:
        return OrderScheduleSnapshotCalendarHelper.normalize_decimal(value)

    @staticmethod
    def _normalize_group_date(value: Any) -> date | None:
        return OrderScheduleSnapshotCalendarHelper.normalize_group_date(value)

    async def aggregate_quantity_by_day(
        self,
        field_name: str,
        start_date: date,
        end_date: date,
    ) -> dict[date, dict[str, Decimal | int]]:
        return await self.calendar_helper.aggregate_quantity_by_day(
            field_name,
            start_date,
            end_date,
        )

    async def aggregate_calendar_distribution(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[date, dict[str, Decimal | int]]:
        return await self.calendar_helper.aggregate_calendar_distribution(
            start_date,
            end_date,
        )

    async def summarize_calendar_day(
        self,
        target_date: date,
    ) -> dict[str, Decimal | int | date]:
        return await self.calendar_helper.summarize_calendar_day(target_date)

    async def get_calendar_day_detail(
        self,
        target_date: date,
    ) -> dict[str, Any]:
        return await self.calendar_helper.get_calendar_day_detail(target_date)

    async def list_by_date_field(
        self,
        field_name: str,
        target_date: date,
    ) -> Sequence[OrderScheduleSnapshot]:
        return await self.calendar_helper.list_by_date_field(field_name, target_date)
