from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class ScheduleSnapshotRefreshSeedOrchestrator:
    """Seed orchestration helpers for snapshot refresh service."""

    async def fast_seed_all(
        self,
        *,
        session: AsyncSession,
        source: str,
        reason: str,
        iter_known_order_line_id_batches: Callable[[], Any],
        build_shared_dynamic_context_for_known_orders: Callable[[], Awaitable[dict[str, Any]]],
        preload_refresh_batch_dependencies: Callable[..., Awaitable[dict[str, Any]]],
        build_seed_rows: Callable[..., list[dict[str, Any]]],
        bulk_upsert_snapshot_rows: Callable[[list[dict[str, Any]]], Awaitable[None]],
    ) -> int:
        total_seeded = 0
        shared_dynamic_context: dict[str, Any] | None = None
        async for order_line_ids in iter_known_order_line_id_batches():
            if shared_dynamic_context is None:
                shared_dynamic_context = await build_shared_dynamic_context_for_known_orders()
            preloaded = await preload_refresh_batch_dependencies(
                order_line_ids,
                include_snapshot_map=False,
                shared_dynamic_context=shared_dynamic_context,
            )
            rows = build_seed_rows(
                order_line_ids=order_line_ids,
                preloaded=preloaded,
                source=source,
                reason=reason,
            )
            if not rows:
                continue
            await bulk_upsert_snapshot_rows(rows)
            total_seeded += len(rows)

        await session.flush()
        return total_seeded
