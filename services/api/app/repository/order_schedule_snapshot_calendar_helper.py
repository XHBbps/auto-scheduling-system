from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, case, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_schedule_snapshot import OrderScheduleSnapshot


class OrderScheduleSnapshotCalendarHelper:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def date_window(start_date: date, end_date: date) -> tuple[datetime, datetime]:
        return (
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.min.time()),
        )

    @staticmethod
    def day_range(target_date: date) -> tuple[datetime, datetime]:
        start = datetime.combine(target_date, datetime.min.time())
        end = start + timedelta(days=1)
        return start, end

    @staticmethod
    def normalize_decimal(value: Any) -> Decimal:
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def normalize_group_date(value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value), "%Y-%m-%d").date()

    async def count_by_date_field_window(
        self,
        field_name: str,
        start_date: date,
        end_date: date,
        *,
        schedule_bucket: str | None = None,
        warning_level: str | None = None,
    ) -> int:
        column = getattr(OrderScheduleSnapshot, field_name)
        start_dt, end_dt = self.date_window(start_date, end_date)
        conditions = [
            column.isnot(None),
            column >= start_dt,
            column < end_dt,
        ]
        if schedule_bucket == "unscheduled":
            conditions.append(OrderScheduleSnapshot.schedule_status != "scheduled")
        elif schedule_bucket == "risk":
            conditions.append(
                (OrderScheduleSnapshot.schedule_status != "scheduled")
                | (OrderScheduleSnapshot.warning_level == "abnormal")
            )
        if warning_level:
            conditions.append(OrderScheduleSnapshot.warning_level == warning_level)

        stmt = select(func.count()).select_from(OrderScheduleSnapshot).where(and_(*conditions))
        return (await self.session.execute(stmt)).scalar_one()

    async def summarize_date_field_window(
        self,
        field_name: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, int]:
        column = getattr(OrderScheduleSnapshot, field_name)
        start_dt, end_dt = self.date_window(start_date, end_date)
        base_conditions = and_(
            column.isnot(None),
            column >= start_dt,
            column < end_dt,
        )
        stmt = select(
            func.count(OrderScheduleSnapshot.id).label("delivery_count"),
            func.sum(case((OrderScheduleSnapshot.schedule_status != "scheduled", 1), else_=0)).label(
                "unscheduled_count"
            ),
            func.sum(case((OrderScheduleSnapshot.warning_level == "abnormal", 1), else_=0)).label("abnormal_count"),
        ).where(base_conditions)
        delivery_count, unscheduled_count, abnormal_count = (await self.session.execute(stmt)).one()
        return {
            "delivery_count": int(delivery_count or 0),
            "unscheduled_count": int(unscheduled_count or 0),
            "abnormal_count": int(abnormal_count or 0),
        }

    async def summarize_date_field_windows(
        self,
        field_name: str,
        windows: Sequence[tuple[str, date, date]],
    ) -> dict[str, dict[str, int]]:
        summaries = {
            bucket: {
                "delivery_count": 0,
                "unscheduled_count": 0,
                "abnormal_count": 0,
            }
            for bucket, _, _ in windows
        }
        if not windows:
            return summaries

        column = getattr(OrderScheduleSnapshot, field_name)
        statements = []
        for bucket, start_date, end_date in windows:
            start_dt, end_dt = self.date_window(start_date, end_date)
            statements.append(
                select(
                    literal(bucket).label("bucket"),
                    func.count(OrderScheduleSnapshot.id).label("delivery_count"),
                    func.sum(case((OrderScheduleSnapshot.schedule_status != "scheduled", 1), else_=0)).label(
                        "unscheduled_count"
                    ),
                    func.sum(case((OrderScheduleSnapshot.warning_level == "abnormal", 1), else_=0)).label(
                        "abnormal_count"
                    ),
                ).where(
                    and_(
                        column.isnot(None),
                        column >= start_dt,
                        column < end_dt,
                    )
                )
            )

        summary_stmt = union_all(*statements) if len(statements) > 1 else statements[0]
        rows = (await self.session.execute(summary_stmt)).all()
        for bucket, delivery_count, unscheduled_count, abnormal_count in rows:
            summaries[bucket] = {
                "delivery_count": int(delivery_count or 0),
                "unscheduled_count": int(unscheduled_count or 0),
                "abnormal_count": int(abnormal_count or 0),
            }
        return summaries

    async def aggregate_quantity_by_day(
        self,
        field_name: str,
        start_date: date,
        end_date: date,
    ) -> dict[date, dict[str, Decimal | int]]:
        column = getattr(OrderScheduleSnapshot, field_name)
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())
        group_day = func.date(column)
        stmt = (
            select(
                group_day.label("calendar_date"),
                func.count(OrderScheduleSnapshot.id).label("order_count"),
                func.coalesce(func.sum(OrderScheduleSnapshot.quantity), 0).label("quantity_sum"),
            )
            .where(
                column.isnot(None),
                column >= start_dt,
                column < end_dt,
            )
            .group_by(group_day)
            .order_by(group_day)
        )
        result = await self.session.execute(stmt)
        aggregated: dict[date, dict[str, Decimal | int]] = {}
        for raw_date, order_count, quantity_sum in result.all():
            day = self.normalize_group_date(raw_date)
            if day is None:
                continue
            aggregated[day] = {
                "order_count": int(order_count or 0),
                "quantity_sum": self.normalize_decimal(quantity_sum),
            }
        return aggregated

    async def aggregate_calendar_distribution(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[date, dict[str, Decimal | int]]:
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())

        def build_field_query(field_name: str, bucket: str):
            column = getattr(OrderScheduleSnapshot, field_name)
            group_day = func.date(column)
            return (
                select(
                    literal(bucket).label("bucket"),
                    group_day.label("calendar_date"),
                    func.count(OrderScheduleSnapshot.id).label("order_count"),
                    func.coalesce(func.sum(OrderScheduleSnapshot.quantity), 0).label("quantity_sum"),
                )
                .where(
                    column.isnot(None),
                    column >= start_dt,
                    column < end_dt,
                )
                .group_by(group_day)
            )

        stmt = union_all(
            build_field_query("confirmed_delivery_date", "delivery"),
            build_field_query("trigger_date", "trigger"),
            build_field_query("planned_start_date", "planned_start"),
        )
        result = await self.session.execute(stmt)

        aggregated: dict[date, dict[str, Decimal | int]] = {}
        metric_map = {
            "delivery": ("delivery_order_count", "delivery_quantity_sum"),
            "trigger": ("trigger_order_count", "trigger_quantity_sum"),
            "planned_start": ("planned_start_order_count", "planned_start_quantity_sum"),
        }
        for bucket, raw_date, order_count, quantity_sum in result.all():
            day = self.normalize_group_date(raw_date)
            metric_keys = metric_map.get(bucket)
            if day is None or metric_keys is None:
                continue
            day_payload = aggregated.setdefault(day, {})
            order_key, quantity_key = metric_keys
            day_payload[order_key] = int(order_count or 0)
            day_payload[quantity_key] = self.normalize_decimal(quantity_sum)
        return aggregated

    async def summarize_calendar_day(
        self,
        target_date: date,
    ) -> dict[str, Decimal | int | date]:
        start_dt, end_dt = self.day_range(target_date)

        def count_case(field_name: str):
            column = getattr(OrderScheduleSnapshot, field_name)
            return func.sum(
                case(
                    (
                        and_(
                            column.isnot(None),
                            column >= start_dt,
                            column < end_dt,
                        ),
                        1,
                    ),
                    else_=0,
                )
            )

        def quantity_case(field_name: str):
            column = getattr(OrderScheduleSnapshot, field_name)
            return func.sum(
                case(
                    (
                        and_(
                            column.isnot(None),
                            column >= start_dt,
                            column < end_dt,
                        ),
                        func.coalesce(OrderScheduleSnapshot.quantity, 0),
                    ),
                    else_=0,
                )
            )

        stmt = select(
            count_case("confirmed_delivery_date").label("delivery_order_count"),
            quantity_case("confirmed_delivery_date").label("delivery_quantity_sum"),
            count_case("trigger_date").label("trigger_order_count"),
            quantity_case("trigger_date").label("trigger_quantity_sum"),
            count_case("planned_start_date").label("planned_start_order_count"),
            quantity_case("planned_start_date").label("planned_start_quantity_sum"),
        )
        (
            delivery_order_count,
            delivery_quantity_sum,
            trigger_order_count,
            trigger_quantity_sum,
            planned_start_order_count,
            planned_start_quantity_sum,
        ) = (await self.session.execute(stmt)).one()

        return {
            "calendar_date": target_date,
            "delivery_order_count": int(delivery_order_count or 0),
            "delivery_quantity_sum": self.normalize_decimal(delivery_quantity_sum),
            "trigger_order_count": int(trigger_order_count or 0),
            "trigger_quantity_sum": self.normalize_decimal(trigger_quantity_sum),
            "planned_start_order_count": int(planned_start_order_count or 0),
            "planned_start_quantity_sum": self.normalize_decimal(planned_start_quantity_sum),
        }

    async def get_calendar_day_detail(
        self,
        target_date: date,
    ) -> dict[str, Any]:
        start_dt, end_dt = self.day_range(target_date)
        delivery_condition = and_(
            OrderScheduleSnapshot.confirmed_delivery_date.isnot(None),
            OrderScheduleSnapshot.confirmed_delivery_date >= start_dt,
            OrderScheduleSnapshot.confirmed_delivery_date < end_dt,
        )
        trigger_condition = and_(
            OrderScheduleSnapshot.trigger_date.isnot(None),
            OrderScheduleSnapshot.trigger_date >= start_dt,
            OrderScheduleSnapshot.trigger_date < end_dt,
        )
        planned_start_condition = and_(
            OrderScheduleSnapshot.planned_start_date.isnot(None),
            OrderScheduleSnapshot.planned_start_date >= start_dt,
            OrderScheduleSnapshot.planned_start_date < end_dt,
        )
        stmt = (
            select(OrderScheduleSnapshot)
            .where(delivery_condition | trigger_condition | planned_start_condition)
            .order_by(
                OrderScheduleSnapshot.confirmed_delivery_date.asc().nullslast(),
                OrderScheduleSnapshot.planned_start_date.asc().nullslast(),
                OrderScheduleSnapshot.order_line_id.asc(),
            )
        )
        rows = list((await self.session.execute(stmt)).scalars().all())

        delivery_orders: list[OrderScheduleSnapshot] = []
        trigger_orders: list[OrderScheduleSnapshot] = []
        planned_start_orders: list[OrderScheduleSnapshot] = []
        delivery_quantity_sum = Decimal("0")
        trigger_quantity_sum = Decimal("0")
        planned_start_quantity_sum = Decimal("0")

        for row in rows:
            quantity = self.normalize_decimal(row.quantity)
            if row.confirmed_delivery_date and start_dt <= row.confirmed_delivery_date < end_dt:
                delivery_orders.append(row)
                delivery_quantity_sum += quantity
            if row.trigger_date and start_dt <= row.trigger_date < end_dt:
                trigger_orders.append(row)
                trigger_quantity_sum += quantity
            if row.planned_start_date and start_dt <= row.planned_start_date < end_dt:
                planned_start_orders.append(row)
                planned_start_quantity_sum += quantity

        return {
            "summary": {
                "calendar_date": target_date,
                "delivery_order_count": len(delivery_orders),
                "delivery_quantity_sum": delivery_quantity_sum,
                "trigger_order_count": len(trigger_orders),
                "trigger_quantity_sum": trigger_quantity_sum,
                "planned_start_order_count": len(planned_start_orders),
                "planned_start_quantity_sum": planned_start_quantity_sum,
            },
            "delivery_orders": delivery_orders,
            "trigger_orders": trigger_orders,
            "planned_start_orders": planned_start_orders,
        }

    async def list_by_date_field(
        self,
        field_name: str,
        target_date: date,
    ) -> Sequence[OrderScheduleSnapshot]:
        column = getattr(OrderScheduleSnapshot, field_name)
        start_dt, end_dt = self.day_range(target_date)
        stmt = (
            select(OrderScheduleSnapshot)
            .where(
                column.isnot(None),
                column >= start_dt,
                column < end_dt,
            )
            .order_by(
                OrderScheduleSnapshot.confirmed_delivery_date.asc().nullslast(),
                OrderScheduleSnapshot.planned_start_date.asc().nullslast(),
                OrderScheduleSnapshot.order_line_id.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
