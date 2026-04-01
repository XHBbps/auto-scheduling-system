from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ScheduleSnapshotRefreshRuntimeOrchestrator:
    """Runtime orchestration helpers for snapshot refresh service wrappers."""

    def __init__(self, *, seed_lock: asyncio.Lock, advisory_lock_key: int):
        self.seed_lock = seed_lock
        self.advisory_lock_key = advisory_lock_key

    async def ensure_seeded(
        self,
        *,
        snapshot_exists_any: Callable[[], Awaitable[bool]],
        ensure_seeded_committed: Callable[[str, str], Awaitable[bool]],
        record_runtime_observation: Callable[..., None],
        duration_ms: Callable[[float], float],
        source: str,
        reason: str,
        started_at: datetime,
        started_perf: float,
    ) -> bool:
        try:
            if await snapshot_exists_any():
                record_runtime_observation(
                    operation="ensure_seeded",
                    source=source,
                    reason=reason,
                    started_at=started_at,
                    duration_ms=duration_ms(started_perf),
                    success=True,
                    summary={"seeded": False, "skipped": True},
                )
                return False
            seeded = await ensure_seeded_committed(source, reason)
            record_runtime_observation(
                operation="ensure_seeded",
                source=source,
                reason=reason,
                started_at=started_at,
                duration_ms=duration_ms(started_perf),
                success=True,
                summary={"seeded": seeded, "skipped": False},
            )
            return seeded
        except Exception as exc:
            record_runtime_observation(
                operation="ensure_seeded",
                source=source,
                reason=reason,
                started_at=started_at,
                duration_ms=duration_ms(started_perf),
                success=False,
                error=repr(exc),
            )
            raise

    async def refresh_one_committed(
        self,
        *,
        session_factory,
        spawn_for_session: Callable[[AsyncSession], Any],
        order_line_id: int,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool,
        record_runtime_observation: Callable[..., None],
        duration_ms: Callable[[float], float],
        started_at: datetime,
        started_perf: float,
    ):
        try:
            async with session_factory() as session:
                service = spawn_for_session(session)
                async with session.begin():
                    snapshot = await service.refresh_one(
                        order_line_id=order_line_id,
                        source=source,
                        reason=reason,
                        force_stale_for_scheduled=force_stale_for_scheduled,
                    )
                record_runtime_observation(
                    operation="refresh_one_committed",
                    source=source,
                    reason=reason,
                    started_at=started_at,
                    duration_ms=duration_ms(started_perf),
                    success=True,
                    summary={
                        "order_line_id": order_line_id,
                        "schedule_status": getattr(snapshot, "schedule_status", None),
                    },
                )
                return snapshot
        except Exception as exc:
            record_runtime_observation(
                operation="refresh_one_committed",
                source=source,
                reason=reason,
                started_at=started_at,
                duration_ms=duration_ms(started_perf),
                success=False,
                error=repr(exc),
                summary={"order_line_id": order_line_id},
            )
            raise

    async def refresh_future_window(
        self,
        *,
        resolve_target_ids: Callable[[int | None], Awaitable[tuple[int, list[int]]]],
        refresh_batch: Callable[..., Awaitable[dict[str, int]]],
        record_runtime_observation: Callable[..., None],
        duration_ms: Callable[[float], float],
        window_days: int | None,
        source: str,
        reason: str,
        force_stale_for_scheduled: bool,
        started_at: datetime,
        started_perf: float,
    ) -> dict[str, int]:
        days = window_days
        try:
            days, order_line_ids = await resolve_target_ids(window_days)
            result = await refresh_batch(
                order_line_ids,
                source=source,
                reason=reason,
                force_stale_for_scheduled=force_stale_for_scheduled,
            )
            record_runtime_observation(
                operation="refresh_future_window",
                source=source,
                reason=reason,
                started_at=started_at,
                duration_ms=duration_ms(started_perf),
                success=True,
                summary={"window_days": days, **result},
            )
            return result
        except Exception as exc:
            record_runtime_observation(
                operation="refresh_future_window",
                source=source,
                reason=reason,
                started_at=started_at,
                duration_ms=duration_ms(started_perf),
                success=False,
                error=repr(exc),
                summary={"window_days": days},
            )
            raise

    async def rebuild_all_open_snapshots(
        self,
        *,
        rebuild_known_order_ids: Callable[[str, str, bool], Awaitable[dict[str, int]]],
        record_runtime_observation: Callable[..., None],
        duration_ms: Callable[[float], float],
        source: str,
        reason: str,
        force_stale_for_scheduled: bool,
        started_at: datetime,
        started_perf: float,
    ) -> dict[str, int]:
        try:
            result = await rebuild_known_order_ids(
                source=source,
                reason=reason,
                force_stale_for_scheduled=force_stale_for_scheduled,
            )
            record_runtime_observation(
                operation="rebuild_all_open_snapshots",
                source=source,
                reason=reason,
                started_at=started_at,
                duration_ms=duration_ms(started_perf),
                success=True,
                summary=result,
            )
            return result
        except Exception as exc:
            record_runtime_observation(
                operation="rebuild_all_open_snapshots",
                source=source,
                reason=reason,
                started_at=started_at,
                duration_ms=duration_ms(started_perf),
                success=False,
                error=repr(exc),
            )
            raise

    async def ensure_seeded_committed(
        self,
        *,
        session_factory,
        spawn_for_session: Callable[[AsyncSession], Any],
        source: str,
        reason: str,
    ) -> bool:
        async with self.seed_lock:
            async with session_factory() as session:
                service = spawn_for_session(session)
                async with session.begin():
                    await self.acquire_seed_lock(session)
                    if await service.snapshot_repo.exists_any():
                        return False

                    seeded = await service._fast_seed_all(source=source, reason=reason)
                    if seeded > 0:
                        logger.info(
                            "Initial snapshot fast seed finished: rows=%s source=%s reason=%s",
                            seeded,
                            source,
                            reason,
                        )
                        return True

                    result = await service._refresh_all_known_order_line_ids_in_batches(
                        source=source,
                        reason=reason,
                    )
                    if result["total"] == 0:
                        return False
                    return True

    async def acquire_seed_lock(self, session: AsyncSession) -> None:
        bind = session.bind
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name != "postgresql":
            return
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": self.advisory_lock_key},
        )
