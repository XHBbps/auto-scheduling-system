import asyncio
import contextlib
import logging
import signal

from app.services.background_task_worker_service import BackgroundTaskWorkerService
from scripts.wait_for_db import wait_for_database

logger = logging.getLogger(__name__)


async def _main() -> None:
    await wait_for_database()
    worker = BackgroundTaskWorkerService()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(_shutdown(worker, s)))

    await worker.run_forever()


async def _shutdown(worker: BackgroundTaskWorkerService, sig: signal.Signals) -> None:
    logger.info("Received signal %s, initiating graceful shutdown...", sig.name)
    worker.stop()


if __name__ == "__main__":
    from app.common.logging_setup import configure_logging

    configure_logging()
    asyncio.run(_main())
