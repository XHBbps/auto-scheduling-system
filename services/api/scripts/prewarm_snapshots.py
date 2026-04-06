import asyncio
import logging

from app.config import settings
from app.database import async_session_factory
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService

logger = logging.getLogger(__name__)


async def prewarm_snapshots() -> None:
    if not settings.snapshot_prewarm_on_startup:
        logger.info("SNAPSHOT_PREWARM_ON_STARTUP=false, skip snapshot prewarm.")
        return

    async with async_session_factory() as session:
        refreshed = await ScheduleSnapshotRefreshService(session).ensure_seeded(
            source="startup",
            reason="startup_prewarm",
        )
        if refreshed:
            logger.info("Snapshot prewarm finished and persisted successfully.")
        else:
            logger.info("Snapshot prewarm skipped because snapshot data already exists.")


if __name__ == "__main__":
    from app.common.logging_setup import configure_logging

    configure_logging()
    asyncio.run(prewarm_snapshots())
