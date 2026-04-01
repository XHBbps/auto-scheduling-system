from __future__ import annotations

from datetime import date
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_schedule_result import MachineScheduleResult
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.services.schedule_snapshot_refresh_helpers import (
    build_dynamic_snapshot_payload,
    build_machine_snapshot_payload,
)


class ScheduleSnapshotRefreshSeedHelper:
    """Seed and known-order batching helpers for snapshot refresh service."""

    def __init__(self, *, session: AsyncSession, today: date):
        self.session = session
        self.today = today

    async def merge_order_line_ids(self, *stmts) -> list[int]:
        normalized_stmts = [self.normalize_order_line_id_stmt(stmt) for stmt in stmts if stmt is not None]
        if not normalized_stmts:
            return []
        merged_stmt = normalized_stmts[0]
        for stmt in normalized_stmts[1:]:
            merged_stmt = merged_stmt.union(stmt)
        merged_subquery = merged_stmt.subquery()
        rows = (
            await self.session.execute(
                select(merged_subquery.c.order_line_id).order_by(merged_subquery.c.order_line_id.asc())
            )
        ).scalars().all()
        return [int(value) for value in rows if value is not None]

    @staticmethod
    def normalize_order_line_id_stmt(stmt):
        subquery = stmt.subquery()
        first_column = list(subquery.c)[0]
        return select(first_column.label("order_line_id"))

    async def count_all_known_order_line_ids(self) -> int:
        subquery = self.known_order_line_ids_subquery()
        stmt = select(func.count()).select_from(subquery)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def list_known_order_line_id_batch(
        self,
        *,
        after_order_line_id: int | None = None,
        limit: int | None = None,
    ) -> list[int]:
        subquery = self.known_order_line_ids_subquery()
        stmt = select(subquery.c.order_line_id).order_by(subquery.c.order_line_id.asc())
        if after_order_line_id is not None:
            stmt = stmt.where(subquery.c.order_line_id > after_order_line_id)
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [int(value) for value in rows if value is not None]

    async def iter_known_order_line_id_batches(self, *, batch_size: int):
        last_order_line_id: int | None = None
        while True:
            batch = await self.list_known_order_line_id_batch(
                after_order_line_id=last_order_line_id,
                limit=batch_size,
            )
            if not batch:
                break
            yield batch
            last_order_line_id = batch[-1]

    @staticmethod
    def known_order_line_ids_subquery():
        sales_stmt = (
            select(SalesPlanOrderLineSrc.id.label("order_line_id"))
            .where(SalesPlanOrderLineSrc.id.is_not(None))
        )
        machine_stmt = (
            select(MachineScheduleResult.order_line_id.label("order_line_id"))
            .where(MachineScheduleResult.order_line_id.is_not(None))
        )
        return sales_stmt.union(machine_stmt).subquery()

    def build_seed_rows(
        self,
        *,
        order_line_ids: Sequence[int],
        preloaded: dict[str, Any],
        source: str,
        reason: str,
    ) -> list[dict[str, Any]]:
        order_map = preloaded["order_map"]
        machine_map = preloaded["machine_map"]
        issue_map = preloaded["issue_map"]
        dynamic_context = preloaded.get("dynamic_context")

        rows: list[dict[str, Any]] = []
        for order_line_id in order_line_ids:
            order = order_map.get(order_line_id)
            machine = machine_map.get(order_line_id)
            issues = issue_map.get(order_line_id, [])

            if machine:
                rows.append(
                    build_machine_snapshot_payload(
                        order_line_id=order_line_id,
                        machine=machine,
                        order=order,
                        issues=issues,
                        source=source,
                        reason=reason,
                        stale_reason=None,
                    )
                )
                continue

            if not order:
                continue

            rows.append(
                build_dynamic_snapshot_payload(
                    today=self.today,
                    order=order,
                    issues=issues,
                    source=source,
                    reason=reason,
                    bom_material_pairs=(dynamic_context or {}).get("bom_material_pairs"),
                    baselines_by_model=(dynamic_context or {}).get("baselines_by_model"),
                    calendar=(dynamic_context or {}).get("calendar"),
                )
            )

        return rows

    async def bulk_upsert_snapshot_rows(self, rows: Sequence[dict[str, Any]], *, batch_size: int) -> None:
        if not rows:
            return
        for start in range(0, len(rows), batch_size):
            chunk = list(rows[start:start + batch_size])
            stmt = pg_insert(OrderScheduleSnapshot).values(chunk)
            stmt = stmt.on_conflict_do_update(
                constraint="uk_order_schedule_snapshot_order_line_id",
                set_={
                    column.name: getattr(stmt.excluded, column.name)
                    for column in OrderScheduleSnapshot.__table__.columns
                    if column.name not in {"id"}
                },
            )
            await self.session.execute(stmt)

    @staticmethod
    def empty_refresh_batch_summary() -> dict[str, int]:
        return {
            "total": 0,
            "refreshed": 0,
            "scheduled": 0,
            "scheduled_stale": 0,
            "deleted": 0,
        }

    @classmethod
    def merge_refresh_batch_summary(
        cls,
        current: dict[str, int],
        incoming: dict[str, int],
    ) -> dict[str, int]:
        merged = dict(current)
        for key in cls.empty_refresh_batch_summary():
            merged[key] = int(merged.get(key, 0)) + int(incoming.get(key, 0))
        return merged
