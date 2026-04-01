import asyncio
import logging
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)


async def wait_for_database() -> None:
    if not settings.wait_for_db_on_startup:
        logger.info("WAIT_FOR_DB_ON_STARTUP=false, skip database wait.")
        return

    deadline = time.monotonic() + max(settings.wait_for_db_timeout_seconds, 1)
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        engine = create_async_engine(settings.database_url, echo=False)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database is ready.")
            return
        except Exception as exc:  # pragma: no cover - startup environment dependent
            last_error = exc
            logger.info("Database not ready yet, retrying in %s seconds...", settings.wait_for_db_poll_interval_seconds)
            await asyncio.sleep(max(settings.wait_for_db_poll_interval_seconds, 0.1))
        finally:
            await engine.dispose()

    raise RuntimeError(
        f"Database was not ready within {settings.wait_for_db_timeout_seconds} seconds."
    ) from last_error


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    asyncio.run(wait_for_database())
