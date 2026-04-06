import asyncio

from app.services.background_task_worker_service import BackgroundTaskWorkerService
from scripts.wait_for_db import wait_for_database


async def _main() -> None:
    await wait_for_database()
    worker = BackgroundTaskWorkerService()
    await worker.run_forever()


if __name__ == "__main__":
    from app.common.logging_setup import configure_logging

    configure_logging()
    asyncio.run(_main())
