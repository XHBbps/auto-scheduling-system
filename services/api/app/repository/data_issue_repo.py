from collections.abc import Sequence
from typing import Any

from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import IssueStatus
from app.common.query_sort_utils import build_sort_expression, resolve_order_by
from app.models.data_issue import DataIssueRecord
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.repository.base import BaseRepository


class DataIssueRepo(BaseRepository[DataIssueRecord]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, DataIssueRecord)

    @staticmethod
    def _normalize_issue_keys(
        *,
        biz_key: str | None,
        order_line_id: int | None,
    ) -> tuple[str | None, int | None]:
        return DataIssueRecord.normalize_order_link(
            biz_key=biz_key,
            order_line_id=order_line_id,
        )

    @staticmethod
    def _normalize_source_system(source_system: str | None) -> str | None:
        return DataIssueRecord.normalize_source_system(source_system)

    @staticmethod
    def _build_open_issue_match_conditions(
        *,
        issue_type: str,
        source_system: str | None,
        issue_title: str,
        biz_key: str | None,
        order_line_id: int | None,
    ) -> list[Any]:
        normalized_source_system = DataIssueRepo._normalize_source_system(source_system)
        conditions = [
            DataIssueRecord.issue_type == issue_type,
            DataIssueRecord.source_system == normalized_source_system,
            DataIssueRecord.status == "open",
        ]
        if order_line_id is not None:
            conditions.append(DataIssueRecord.order_line_id == order_line_id)
        else:
            conditions.append(DataIssueRecord.issue_title == issue_title)
            conditions.append(DataIssueRecord.biz_key == biz_key)
        return conditions

    @staticmethod
    def _mark_duplicate_issue_resolved(entity: DataIssueRecord, canonical_id: int) -> None:
        entity.status = IssueStatus.RESOLVED
        entity.remark = f"auto-deduped into open issue {canonical_id}"

    async def _find_latest_matching_open_issue(
        self,
        *,
        match_conditions: list[Any],
    ) -> DataIssueRecord | None:
        stmt = select(DataIssueRecord).where(and_(*match_conditions)).order_by(desc(DataIssueRecord.id))
        matches = (await self.session.execute(stmt)).scalars().all()
        if not matches:
            return None

        canonical = matches[0]
        duplicates = matches[1:]
        for duplicate in duplicates:
            self._mark_duplicate_issue_resolved(duplicate, canonical.id)
        if duplicates:
            await self.session.flush()
        return canonical

    async def paginate(
        self, page_no: int = 1, page_size: int = 20, **filters: Any
    ) -> tuple[Sequence[DataIssueRecord], int]:
        sort_field = filters.pop("sort_field", None)
        sort_order = filters.pop("sort_order", None)
        base = select(DataIssueRecord)
        count_base = select(func.count()).select_from(DataIssueRecord)

        conditions = []
        if filters.get("status"):
            conditions.append(DataIssueRecord.status == filters["status"])
        if filters.get("issue_type"):
            conditions.append(DataIssueRecord.issue_type == filters["issue_type"])
        if filters.get("biz_key"):
            conditions.append(DataIssueRecord.biz_key == filters["biz_key"])
        if "order_line_id" in filters and filters["order_line_id"] is not None:
            conditions.append(DataIssueRecord.order_line_id == filters["order_line_id"])
        if filters.get("source_system"):
            conditions.append(DataIssueRecord.source_system == filters["source_system"])

        if conditions:
            base = base.where(and_(*conditions))
            count_base = count_base.where(and_(*conditions))

        total = (await self.session.execute(count_base)).scalar_one()
        sort_expression = build_sort_expression(
            sort_field=sort_field,
            sort_order=sort_order,
            allowed_fields={
                "id": DataIssueRecord.id,
                "issue_type": DataIssueRecord.issue_type,
                "issue_level": DataIssueRecord.issue_level,
                "source_system": DataIssueRecord.source_system,
                "biz_key": DataIssueRecord.biz_key,
                "issue_title": DataIssueRecord.issue_title,
                "status": DataIssueRecord.status,
                "created_at": DataIssueRecord.created_at,
            },
        )
        stmt = (
            base.order_by(
                *resolve_order_by(
                    sort_expression=sort_expression,
                    default_order_by=[DataIssueRecord.id.desc()],
                )
            )
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return items, total

    async def paginate_with_snapshot(
        self, page_no: int = 1, page_size: int = 20, **filters: Any
    ) -> tuple[Sequence[tuple[DataIssueRecord, OrderScheduleSnapshot | None]], int]:
        sort_field = filters.pop("sort_field", None)
        sort_order = filters.pop("sort_order", None)
        base = select(DataIssueRecord, OrderScheduleSnapshot).outerjoin(
            OrderScheduleSnapshot,
            OrderScheduleSnapshot.order_line_id == DataIssueRecord.order_line_id,
        )
        count_base = select(func.count()).select_from(DataIssueRecord)

        conditions = []
        if filters.get("status"):
            conditions.append(DataIssueRecord.status == filters["status"])
        if filters.get("issue_type"):
            conditions.append(DataIssueRecord.issue_type == filters["issue_type"])
        if filters.get("biz_key"):
            conditions.append(DataIssueRecord.biz_key == filters["biz_key"])
        if "order_line_id" in filters and filters["order_line_id"] is not None:
            conditions.append(DataIssueRecord.order_line_id == filters["order_line_id"])
        if filters.get("source_system"):
            conditions.append(DataIssueRecord.source_system == filters["source_system"])

        if conditions:
            where = and_(*conditions)
            base = base.where(where)
            count_base = count_base.where(where)

        total = (await self.session.execute(count_base)).scalar_one()
        sort_expression = build_sort_expression(
            sort_field=sort_field,
            sort_order=sort_order,
            allowed_fields={
                "id": DataIssueRecord.id,
                "issue_type": DataIssueRecord.issue_type,
                "issue_level": DataIssueRecord.issue_level,
                "source_system": DataIssueRecord.source_system,
                "biz_key": DataIssueRecord.biz_key,
                "issue_title": DataIssueRecord.issue_title,
                "status": DataIssueRecord.status,
                "created_at": DataIssueRecord.created_at,
            },
        )
        stmt = (
            base.order_by(
                *resolve_order_by(
                    sort_expression=sort_expression,
                    default_order_by=[DataIssueRecord.id.desc()],
                )
            )
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.session.execute(stmt)).all()
        return items, total

    async def upsert_open_issue(
        self,
        *,
        issue_type: str,
        issue_level: str | None,
        source_system: str | None,
        biz_key: str | None,
        order_line_id: int | None,
        issue_title: str,
        issue_detail: str | None,
    ) -> DataIssueRecord:
        biz_key, order_line_id = self._normalize_issue_keys(
            biz_key=biz_key,
            order_line_id=order_line_id,
        )
        source_system = self._normalize_source_system(source_system)
        match_conditions = self._build_open_issue_match_conditions(
            issue_type=issue_type,
            source_system=source_system,
            issue_title=issue_title,
            biz_key=biz_key,
            order_line_id=order_line_id,
        )

        existing = await self._find_latest_matching_open_issue(
            match_conditions=match_conditions,
        )
        if existing:
            existing.issue_level = issue_level
            existing.issue_title = issue_title
            existing.issue_detail = issue_detail
            existing.biz_key = biz_key
            existing.order_line_id = order_line_id
            await self.session.flush()
            return existing

        entity = DataIssueRecord(
            issue_type=issue_type,
            issue_level=issue_level,
            source_system=source_system,
            biz_key=biz_key,
            order_line_id=order_line_id,
            issue_title=issue_title,
            issue_detail=issue_detail,
            status="open",
        )
        return await self.add(entity)

    async def list_open_by_order_line_ids(
        self,
        order_line_ids: Sequence[int],
    ) -> Sequence[DataIssueRecord]:
        if not order_line_ids:
            return []
        stmt = (
            select(DataIssueRecord)
            .where(
                and_(
                    DataIssueRecord.status == "open",
                    DataIssueRecord.order_line_id.in_(order_line_ids),
                )
            )
            .order_by(DataIssueRecord.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_biz_key_and_source_system(
        self,
        *,
        biz_key: str,
        source_system: str,
    ) -> int:
        stmt = delete(DataIssueRecord).where(
            and_(
                DataIssueRecord.biz_key == biz_key,
                DataIssueRecord.source_system == source_system,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
