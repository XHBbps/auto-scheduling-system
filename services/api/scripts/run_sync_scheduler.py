import asyncio
import logging

from app.sync_scheduler import SyncSchedulerService
from scripts.wait_for_db import wait_for_database


async def _main() -> None:
    await wait_for_database()
    scheduler = SyncSchedulerService()
    await scheduler.run_forever()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    asyncio.run(_main())
