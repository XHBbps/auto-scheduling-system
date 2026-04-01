from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Any, Sequence

from sqlalchemy import Integer, and_, case, delete, func, literal, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.query_sort_utils import build_sort_expression, resolve_order_by
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.part_schedule_result import PartScheduleResult
from app.repository.base import BaseRepository


class PartScheduleResultRepo(BaseRepository[PartScheduleResult]):
    SNAPSHOT_FIELDS = {
        "contract_no": OrderScheduleSnapshot.contract_no,
        "order_no": OrderScheduleSnapshot.order_no,
        "customer_name": OrderScheduleSnapshot.customer_name,
        "product_series": OrderScheduleSnapshot.product_series,
        "product_model": OrderScheduleSnapshot.product_model,
        "product_name": OrderScheduleSnapshot.product_name,
        "material_no": OrderScheduleSnapshot.material_no,
        "plant": OrderScheduleSnapshot.plant,
        "quantity": OrderScheduleSnapshot.quantity,
        "order_type": OrderScheduleSnapshot.order_type,
        "custom_no": OrderScheduleSnapshot.custom_no,
        "business_group": OrderScheduleSnapshot.business_group,
        "sales_person_name": OrderScheduleSnapshot.sales_person_name,
        "sales_branch_company": OrderScheduleSnapshot.sales_branch_company,
        "sales_sub_branch": OrderScheduleSnapshot.sales_sub_branch,
        "order_date": OrderScheduleSnapshot.order_date,
        "confirmed_delivery_date": OrderScheduleSnapshot.confirmed_delivery_date,
        "line_total_amount": OrderScheduleSnapshot.line_total_amount,
    }

    PART_FIELDS = {
        "order_line_id": PartScheduleResult.order_line_id,
        "assembly_name": PartScheduleResult.assembly_name,
        "parent_material_no": PartScheduleResult.parent_material_no,
        "parent_name": PartScheduleResult.parent_name,
        "node_level": PartScheduleResult.node_level,
        "bom_path": PartScheduleResult.bom_path,
        "part_name": PartScheduleResult.part_name,
        "part_material_no": PartScheduleResult.part_material_no,
        "production_sequence": PartScheduleResult.production_sequence,
        "assembly_time_days": PartScheduleResult.assembly_time_days,
        "part_cycle_days": PartScheduleResult.part_cycle_days,
        "is_key_part": PartScheduleResult.is_key_part,
        "planned_start_date": PartScheduleResult.planned_start_date,
        "planned_end_date": PartScheduleResult.planned_end_date,
        "warning_level": PartScheduleResult.warning_level,
    }

    def __init__(self, session: AsyncSession):
        super().__init__(session, PartScheduleResult)

    @staticmethod
    def _visible_part_row_condition():
        return or_(
            PartScheduleResult.part_material_no.isnot(None),
            PartScheduleResult.part_name.isnot(None),
            PartScheduleResult.key_part_material_no.isnot(None),
            PartScheduleResult.key_part_name.isnot(None),
        )

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

    @classmethod
    def is_snapshot_field(cls, field_name: str | None) -> bool:
        return bool(field_name and field_name in cls.SNAPSHOT_FIELDS)

    @classmethod
    def build_allowed_sort_fields(cls) -> dict[str, Any]:
        return {
            **cls.PART_FIELDS,
            **cls.SNAPSHOT_FIELDS,
        }

    @staticmethod
    def _default_part_order_by() -> list[Any]:
        return [
            PartScheduleResult.production_sequence.asc(),
            PartScheduleResult.assembly_name.asc(),
            PartScheduleResult.is_key_part.desc(),
            PartScheduleResult.node_level.asc(),
            PartScheduleResult.bom_path.asc(),
            PartScheduleResult.part_material_no.asc(),
        ]

    def _build_list_conditions(self, filters: dict[str, Any]) -> tuple[list[Any], bool]:
        conditions = [self._visible_part_row_condition()]
        needs_snapshot_join = bool(
            filters.get("contract_no")
            or filters.get("order_no")
            or filters.get("plant")
        )

        if filters.get("order_line_id"):
            conditions.append(PartScheduleResult.order_line_id == filters["order_line_id"])
        if filters.get("contract_no"):
            conditions.append(OrderScheduleSnapshot.contract_no.ilike(f"%{filters['contract_no']}%"))
        if filters.get("order_no"):
            conditions.append(OrderScheduleSnapshot.order_no.ilike(f"%{filters['order_no']}%"))
        if filters.get("plant"):
            conditions.append(OrderScheduleSnapshot.plant == filters["plant"])
        if filters.get("assembly_name"):
            conditions.append(PartScheduleResult.assembly_name == filters["assembly_name"])
        if filters.get("part_material_no"):
            conditions.append(PartScheduleResult.part_material_no.ilike(f"%{filters['part_material_no']}%"))
        if filters.get("key_part_name"):
            conditions.append(PartScheduleResult.key_part_name.ilike(f"%{filters['key_part_name']}%"))
        if filters.get("key_part_material_no"):
            conditions.append(PartScheduleResult.key_part_material_no.ilike(f"%{filters['key_part_material_no']}%"))
        if filters.get("warning_level"):
            conditions.append(PartScheduleResult.warning_level == filters["warning_level"])

        date_from = self._parse_date_start(filters.get("date_from"))
        date_to = self._parse_date_end(filters.get("date_to"))
        if date_from:
            conditions.append(PartScheduleResult.planned_end_date >= date_from)
        if date_to:
            conditions.append(PartScheduleResult.planned_end_date < date_to)
        return conditions, needs_snapshot_join

    def _build_export_conditions(self, filters: dict[str, Any]) -> list[Any]:
        conditions, _ = self._build_list_conditions(filters)

        if filters.get("customer_name"):
            conditions.append(OrderScheduleSnapshot.customer_name.ilike(f"%{filters['customer_name']}%"))
        if filters.get("product_series"):
            conditions.append(OrderScheduleSnapshot.product_series == filters["product_series"])
        if filters.get("product_model"):
            conditions.append(OrderScheduleSnapshot.product_model.ilike(f"%{filters['product_model']}%"))
        if filters.get("schedule_status"):
            conditions.append(OrderScheduleSnapshot.schedule_status == filters["schedule_status"])
        return conditions

    async def paginate(
        self, page_no: int = 1, page_size: int = 20, **filters: Any
    ) -> tuple[Sequence[tuple[PartScheduleResult, OrderScheduleSnapshot | None]], int]:
        sort_field = filters.pop("sort_field", None)
        sort_order = filters.pop("sort_order", None)
        conditions, needs_snapshot_join_in_count = self._build_list_conditions(filters)

        base = select(PartScheduleResult, OrderScheduleSnapshot).join(
            OrderScheduleSnapshot,
            OrderScheduleSnapshot.order_line_id == PartScheduleResult.order_line_id,
            isouter=True,
        )
        count_base = select(func.count()).select_from(PartScheduleResult)
        if needs_snapshot_join_in_count:
            count_base = count_base.join(
                OrderScheduleSnapshot,
                OrderScheduleSnapshot.order_line_id == PartScheduleResult.order_line_id,
            )

        if conditions:
            base = base.where(and_(*conditions))
            count_base = count_base.where(and_(*conditions))

        total = (await self.session.execute(count_base)).scalar_one()
        sort_expression = build_sort_expression(
            sort_field=sort_field,
            sort_order=sort_order,
            allowed_fields=self.build_allowed_sort_fields(),
        )
        stmt = base.order_by(
            *resolve_order_by(
                sort_expression=sort_expression,
                default_order_by=[
                    PartScheduleResult.order_line_id.desc(),
                    *self._default_part_order_by(),
                ],
            )
        ).offset((page_no - 1) * page_size).limit(page_size)
        items = (await self.session.execute(stmt)).all()
        return items, total

    async def delete_by_order_line_id(self, order_line_id: int) -> int:
        stmt = delete(PartScheduleResult).where(
            PartScheduleResult.order_line_id == order_line_id
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def find_by_order_line_id(self, order_line_id: int) -> Sequence[PartScheduleResult]:
        stmt = select(PartScheduleResult).where(
            and_(
                PartScheduleResult.order_line_id == order_line_id,
                self._visible_part_row_condition(),
            )
        ).order_by(
            PartScheduleResult.production_sequence,
            PartScheduleResult.assembly_name,
            PartScheduleResult.is_key_part.desc(),
            PartScheduleResult.node_level.asc(),
            PartScheduleResult.bom_path.asc(),
            PartScheduleResult.part_material_no,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_for_export(self, **filters: Any) -> int:
        conditions = self._build_export_conditions(filters)
        stmt = select(func.count()).select_from(PartScheduleResult).join(
            OrderScheduleSnapshot,
            OrderScheduleSnapshot.order_line_id == PartScheduleResult.order_line_id,
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def has_export_rows_beyond_limit(
        self,
        *,
        max_rows: int,
        **filters: Any,
    ) -> bool:
        conditions = self._build_export_conditions(filters)
        stmt = (
            select(PartScheduleResult.id)
            .select_from(PartScheduleResult)
            .join(
                OrderScheduleSnapshot,
                OrderScheduleSnapshot.order_line_id == PartScheduleResult.order_line_id,
            )
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.offset(max(int(max_rows), 0)).limit(1)
        return (await self.session.execute(stmt)).first() is not None

    async def stream_for_export_rows(
        self,
        *,
        batch_size: int,
        snapshot_sort_field: str | None = None,
        snapshot_sort_order: str | None = None,
        part_sort_field: str | None = None,
        part_sort_order: str | None = None,
        **filters: Any,
    ) -> AsyncIterator[list[tuple[OrderScheduleSnapshot, PartScheduleResult]]]:
        conditions = self._build_export_conditions(filters)
        snapshot_sort_expression = build_sort_expression(
            sort_field=snapshot_sort_field,
            sort_order=snapshot_sort_order,
            allowed_fields=self.SNAPSHOT_FIELDS,
        )
        part_sort_expression = build_sort_expression(
            sort_field=part_sort_field,
            sort_order=part_sort_order,
            allowed_fields=self.PART_FIELDS,
        )
        stmt = (
            select(OrderScheduleSnapshot, PartScheduleResult)
            .join(
                OrderScheduleSnapshot,
                OrderScheduleSnapshot.order_line_id == PartScheduleResult.order_line_id,
            )
            .order_by(
                *resolve_order_by(
                    sort_expression=snapshot_sort_expression,
                    default_order_by=[
                        OrderScheduleSnapshot.confirmed_delivery_date.asc().nullslast(),
                        OrderScheduleSnapshot.order_line_id.desc(),
                    ],
                ),
                *resolve_order_by(
                    sort_expression=part_sort_expression,
                    default_order_by=self._default_part_order_by(),
                ),
            )
            .execution_options(
                stream_results=True,
                yield_per=max(int(batch_size), 1),
            )
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.session.stream(stmt)
        try:
            async for partition in result.partitions(max(int(batch_size), 1)):
                batch = [(snapshot, part) for snapshot, part in partition]
                if batch:
                    yield batch
        finally:
            await result.close()

    async def find_by_order_line_ids(
        self,
        order_line_ids: Sequence[int],
        *,
        sort_field: str | None = None,
        sort_order: str | None = None,
    ) -> Sequence[PartScheduleResult]:
        if not order_line_ids:
            return []

        needs_snapshot_join = self.is_snapshot_field(sort_field)
        stmt = select(PartScheduleResult)
        if needs_snapshot_join:
            stmt = stmt.join(
                OrderScheduleSnapshot,
                OrderScheduleSnapshot.order_line_id == PartScheduleResult.order_line_id,
            )

        sort_expression = build_sort_expression(
            sort_field=sort_field,
            sort_order=sort_order,
            allowed_fields=self.build_allowed_sort_fields(),
        )
        stmt = stmt.where(
            and_(
                PartScheduleResult.order_line_id.in_(order_line_ids),
                self._visible_part_row_condition(),
            )
        ).order_by(
            *resolve_order_by(
                sort_expression=sort_expression,
                default_order_by=[
                    PartScheduleResult.order_line_id.desc(),
                    *self._default_part_order_by(),
                ],
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_all(self) -> int:
        stmt = (
            select(func.count())
            .select_from(PartScheduleResult)
            .where(self._visible_part_row_condition())
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def get_dashboard_summary(
        self,
        *,
        top_assembly_limit: int = 10,
    ) -> dict[str, Any]:
        visible_condition = self._visible_part_row_condition()
        assembly_counts_subquery = (
            select(
                PartScheduleResult.assembly_name.label("group_key"),
                func.count().label("item_count"),
            )
            .where(
                and_(
                    PartScheduleResult.assembly_name.isnot(None),
                    visible_condition,
                )
            )
            .group_by(PartScheduleResult.assembly_name)
            .subquery()
        )
        ranked_assemblies_subquery = (
            select(
                literal("assembly").label("bucket"),
                assembly_counts_subquery.c.group_key,
                assembly_counts_subquery.c.item_count,
                func.row_number().over(
                    order_by=(
                        assembly_counts_subquery.c.item_count.desc(),
                        assembly_counts_subquery.c.group_key.asc(),
                    )
                ).label("row_num"),
            )
            .subquery()
        )
        grouped_stmt = union_all(
            select(
                literal("summary").label("bucket"),
                literal(None).label("group_key"),
                func.count(PartScheduleResult.id).label("item_count"),
                func.sum(
                    case((PartScheduleResult.warning_level == "abnormal", 1), else_=0)
                ).label("metric_one"),
                literal(None).cast(Integer).label("row_num"),
            )
            .where(visible_condition),
            select(
                literal("warning_level").label("bucket"),
                PartScheduleResult.warning_level.label("group_key"),
                func.count().label("item_count"),
                literal(None).cast(Integer).label("metric_one"),
                literal(None).cast(Integer).label("row_num"),
            )
            .where(visible_condition)
            .group_by(PartScheduleResult.warning_level),
            select(
                ranked_assemblies_subquery.c.bucket,
                ranked_assemblies_subquery.c.group_key,
                ranked_assemblies_subquery.c.item_count,
                literal(None).cast(Integer).label("metric_one"),
                ranked_assemblies_subquery.c.row_num,
            ).where(ranked_assemblies_subquery.c.row_num <= top_assembly_limit),
        )
        grouped_rows = (await self.session.execute(grouped_stmt)).all()

        total_parts = 0
        abnormal_parts = 0
        warning_counts: list[tuple[str, int]] = []
        top_assemblies: list[tuple[int, str, int]] = []
        for bucket, group_key, item_count, metric_one, row_num in grouped_rows:
            count = int(item_count or 0)
            if bucket == "summary":
                total_parts = count
                abnormal_parts = int(metric_one or 0)
            elif bucket == "warning_level" and group_key:
                warning_counts.append((group_key, count))
            elif bucket == "assembly" and group_key:
                top_assemblies.append((int(row_num or 0), group_key, count))

        warning_counts.sort(key=lambda item: item[0])
        top_assemblies.sort(key=lambda item: item[0])
        return {
            "total_parts": total_parts,
            "abnormal_parts": abnormal_parts,
            "warning_counts": [(group_key, count) for group_key, count in warning_counts],
            "top_assemblies": [(assembly_name, count) for _, assembly_name, count in top_assemblies],
        }

    async def count_abnormal(self) -> int:
        stmt = (
            select(func.count())
            .select_from(PartScheduleResult)
            .where(
                and_(
                    PartScheduleResult.warning_level == "abnormal",
                    self._visible_part_row_condition(),
                )
            )
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def count_by_warning_level(self) -> list[tuple[str, int]]:
        stmt = (
            select(PartScheduleResult.warning_level, func.count())
            .where(self._visible_part_row_condition())
            .group_by(PartScheduleResult.warning_level)
            .order_by(PartScheduleResult.warning_level)
        )
        result = await self.session.execute(stmt)
        return [(level, count) for level, count in result.all() if level]

    async def top_assembly_counts(self, limit: int = 10) -> list[tuple[str, int]]:
        stmt = (
            select(PartScheduleResult.assembly_name, func.count())
            .where(
                and_(
                    PartScheduleResult.assembly_name.isnot(None),
                    self._visible_part_row_condition(),
                )
            )
            .group_by(PartScheduleResult.assembly_name)
            .order_by(func.count().desc(), PartScheduleResult.assembly_name.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [(assembly_name, count) for assembly_name, count in result.all() if assembly_name]
