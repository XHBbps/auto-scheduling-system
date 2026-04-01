from typing import Sequence

from app.common.datetime_utils import utc_now

from sqlalchemy import and_, case, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import BomBackfillQueueStatus
from app.models.bom_backfill_queue import BomBackfillQueue
from app.repository.base import BaseRepository


class BomBackfillQueueRepo(BaseRepository[BomBackfillQueue]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, BomBackfillQueue)

    async def get_by_material_and_plant(
        self,
        material_no: str,
        plant: str,
    ) -> BomBackfillQueue | None:
        stmt = select(BomBackfillQueue).where(
            BomBackfillQueue.material_no == material_no,
            BomBackfillQueue.plant == plant,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def find_by_material_plants(
        self,
        items: Sequence[tuple[str, str]],
    ) -> dict[tuple[str, str], BomBackfillQueue]:
        pairs = list(dict.fromkeys((str(material_no), str(plant)) for material_no, plant in items))
        if not pairs:
            return {}
        stmt = select(BomBackfillQueue).where(
            tuple_(BomBackfillQueue.material_no, BomBackfillQueue.plant).in_(pairs)
        )
        entities = (await self.session.execute(stmt)).scalars().all()
        return {(entity.material_no, entity.plant): entity for entity in entities}

    async def find_by_ids(self, ids: Sequence[int]) -> dict[int, BomBackfillQueue]:
        unique_ids = list(dict.fromkeys(int(item_id) for item_id in ids))
        if not unique_ids:
            return {}
        stmt = select(BomBackfillQueue).where(BomBackfillQueue.id.in_(unique_ids))
        entities = (await self.session.execute(stmt)).scalars().all()
        return {int(entity.id): entity for entity in entities if entity.id is not None}

    async def claim_batch(self, limit: int) -> list[BomBackfillQueue]:
        now = utc_now()
        stmt = (
            select(BomBackfillQueue)
            .where(
                or_(
                    BomBackfillQueue.status == BomBackfillQueueStatus.PENDING.value,
                    and_(
                        BomBackfillQueue.status == BomBackfillQueueStatus.RETRY_WAIT.value,
                        BomBackfillQueue.next_retry_at.is_not(None),
                        BomBackfillQueue.next_retry_at <= now,
                    ),
                )
            )
            .order_by(
                BomBackfillQueue.priority.asc(),
                BomBackfillQueue.first_detected_at.asc(),
                BomBackfillQueue.id.asc(),
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        entities = (await self.session.execute(stmt)).scalars().all()
        for entity in entities:
            entity.status = BomBackfillQueueStatus.PROCESSING.value
            entity.last_attempt_at = now
        await self.session.flush()
        return list(entities)

    async def list_page(
        self,
        *,
        page_no: int,
        page_size: int,
        status: str | None = None,
        failure_kind: str | None = None,
        material_no: str | None = None,
        source: str | None = None,
    ) -> tuple[int, Sequence[BomBackfillQueue]]:
        filters = []
        if status:
            filters.append(BomBackfillQueue.status == status)
        if failure_kind:
            filters.append(BomBackfillQueue.failure_kind == failure_kind)
        if material_no:
            filters.append(BomBackfillQueue.material_no.contains(material_no))
        if source:
            filters.append(BomBackfillQueue.source == source)

        stmt = select(BomBackfillQueue)
        count_stmt = select(func.count()).select_from(BomBackfillQueue)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        total = int((await self.session.execute(count_stmt)).scalar() or 0)
        stmt = stmt.order_by(BomBackfillQueue.updated_at.desc(), BomBackfillQueue.id.desc())
        stmt = stmt.offset((page_no - 1) * page_size).limit(page_size)
        items = (await self.session.execute(stmt)).scalars().all()
        return total, items

    async def count_by_status(self) -> dict[str, int]:
        stmt = (
            select(BomBackfillQueue.status, func.count())
            .group_by(BomBackfillQueue.status)
        )
        rows = (await self.session.execute(stmt)).all()
        return {status: int(count) for status, count in rows}

    async def count_retry_wait_due(self) -> int:
        now = utc_now()
        stmt = select(func.count()).select_from(BomBackfillQueue).where(
            BomBackfillQueue.status == BomBackfillQueueStatus.RETRY_WAIT.value,
            BomBackfillQueue.next_retry_at.is_not(None),
            BomBackfillQueue.next_retry_at <= now,
        )
        return int((await self.session.execute(stmt)).scalar() or 0)

    async def count_failure_kind(self) -> dict[str, int]:
        stmt = (
            select(BomBackfillQueue.failure_kind, func.count())
            .where(BomBackfillQueue.failure_kind.is_not(None))
            .group_by(BomBackfillQueue.failure_kind)
        )
        rows = (await self.session.execute(stmt)).all()
        return {failure_kind: int(count) for failure_kind, count in rows if failure_kind}

    async def get_oldest_pending(self) -> BomBackfillQueue | None:
        now = utc_now()
        stmt = (
            select(BomBackfillQueue)
            .where(
                or_(
                    BomBackfillQueue.status == BomBackfillQueueStatus.PENDING.value,
                    and_(
                        BomBackfillQueue.status == BomBackfillQueueStatus.RETRY_WAIT.value,
                        BomBackfillQueue.next_retry_at.is_not(None),
                        BomBackfillQueue.next_retry_at <= now,
                    ),
                )
            )
            .order_by(BomBackfillQueue.first_detected_at.asc(), BomBackfillQueue.id.asc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_recent_failed(self, limit: int = 5) -> Sequence[BomBackfillQueue]:
        stmt = (
            select(BomBackfillQueue)
            .where(
                BomBackfillQueue.status.in_([
                    BomBackfillQueueStatus.RETRY_WAIT.value,
                    BomBackfillQueueStatus.FAILED.value,
                ])
            )
            .order_by(BomBackfillQueue.updated_at.desc(), BomBackfillQueue.id.desc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    @staticmethod
    def _serialize_observability_item(row) -> dict[str, object | None]:
        return {
            "id": row.id,
            "material_no": row.material_no,
            "plant": row.plant,
            "status": row.status,
            "failure_kind": row.failure_kind,
            "fail_count": row.fail_count,
            "last_error": row.last_error,
            "next_retry_at": row.next_retry_at.isoformat() if row.next_retry_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    async def get_observability_summary(self, limit: int = 5) -> dict[str, object]:
        now = utc_now()
        failed_statuses = [
            BomBackfillQueueStatus.RETRY_WAIT.value,
            BomBackfillQueueStatus.FAILED.value,
        ]
        due_retry_condition = and_(
            BomBackfillQueue.status == BomBackfillQueueStatus.RETRY_WAIT.value,
            BomBackfillQueue.next_retry_at.is_not(None),
            BomBackfillQueue.next_retry_at <= now,
        )
        pending_condition = or_(
            BomBackfillQueue.status == BomBackfillQueueStatus.PENDING.value,
            due_retry_condition,
        )
        aggregate_stmt = select(
            func.coalesce(
                func.sum(case((BomBackfillQueue.status == BomBackfillQueueStatus.PENDING.value, 1), else_=0)),
                0,
            ).label("pending"),
            func.coalesce(
                func.sum(case((BomBackfillQueue.status == BomBackfillQueueStatus.PROCESSING.value, 1), else_=0)),
                0,
            ).label("processing"),
            func.coalesce(
                func.sum(case((BomBackfillQueue.status == BomBackfillQueueStatus.RETRY_WAIT.value, 1), else_=0)),
                0,
            ).label("retry_wait"),
            func.coalesce(
                func.sum(case((BomBackfillQueue.status == BomBackfillQueueStatus.SUCCESS.value, 1), else_=0)),
                0,
            ).label("success"),
            func.coalesce(
                func.sum(case((BomBackfillQueue.status == BomBackfillQueueStatus.FAILED.value, 1), else_=0)),
                0,
            ).label("failed"),
            func.coalesce(
                func.sum(case((BomBackfillQueue.status == BomBackfillQueueStatus.PAUSED.value, 1), else_=0)),
                0,
            ).label("paused"),
            func.coalesce(func.sum(case((due_retry_condition, 1), else_=0)), 0).label("retry_wait_due"),
            func.min(case((pending_condition, BomBackfillQueue.first_detected_at), else_=None)).label(
                "oldest_pending_at"
            ),
        )
        aggregate_row = (await self.session.execute(aggregate_stmt)).one()
        detail_subquery = (
            select(
                BomBackfillQueue.id.label("id"),
                BomBackfillQueue.material_no.label("material_no"),
                BomBackfillQueue.plant.label("plant"),
                BomBackfillQueue.status.label("status"),
                BomBackfillQueue.failure_kind.label("failure_kind"),
                BomBackfillQueue.fail_count.label("fail_count"),
                BomBackfillQueue.last_error.label("last_error"),
                BomBackfillQueue.next_retry_at.label("next_retry_at"),
                BomBackfillQueue.updated_at.label("updated_at"),
                func.count().over(partition_by=BomBackfillQueue.failure_kind).label("failure_kind_count"),
                func.row_number().over(
                    order_by=(
                        case((BomBackfillQueue.status.in_(failed_statuses), 0), else_=1).asc(),
                        BomBackfillQueue.updated_at.desc(),
                        BomBackfillQueue.id.desc(),
                    )
                ).label("latest_rank"),
            )
            .where(
                or_(
                    BomBackfillQueue.failure_kind.is_not(None),
                    BomBackfillQueue.status.in_(failed_statuses),
                )
            )
            .subquery()
        )
        detail_rows = (
            await self.session.execute(
                select(detail_subquery).order_by(detail_subquery.c.latest_rank.asc(), detail_subquery.c.id.desc())
            )
        ).all()
        failure_kind_counts: dict[str, int] = {}
        latest_failed_items: list[dict[str, object | None]] = []
        for row in detail_rows:
            if row.failure_kind and row.failure_kind not in failure_kind_counts:
                failure_kind_counts[str(row.failure_kind)] = int(row.failure_kind_count or 0)
            if len(latest_failed_items) < limit and row.status in failed_statuses:
                latest_failed_items.append(self._serialize_observability_item(row))
        return {
            "status_counts": {
                "pending": int(aggregate_row.pending or 0),
                "processing": int(aggregate_row.processing or 0),
                "retry_wait": int(aggregate_row.retry_wait or 0),
                "success": int(aggregate_row.success or 0),
                "failed": int(aggregate_row.failed or 0),
                "paused": int(aggregate_row.paused or 0),
            },
            "retry_wait_due": int(aggregate_row.retry_wait_due or 0),
            "oldest_pending_at": aggregate_row.oldest_pending_at,
            "failure_kind_counts": failure_kind_counts,
            "latest_failed_items": latest_failed_items,
        }
