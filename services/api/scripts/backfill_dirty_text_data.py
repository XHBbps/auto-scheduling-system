import argparse
import asyncio
import json
import logging

from app.database import async_session_factory
from app.services.historical_text_backfill_service import HistoricalTextBackfillService

logger = logging.getLogger(__name__)


async def run(dry_run: bool) -> None:
    async with async_session_factory() as session:
        result = await HistoricalTextBackfillService(session).backfill(dry_run=dry_run)
        logger.info("Historical text backfill finished: %s", json.dumps(result, ensure_ascii=False, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical dirty text data.")
    parser.add_argument("--dry-run", action="store_true", help="Only calculate changes without committing.")
    args = parser.parse_args()

    from app.common.logging_setup import configure_logging

    configure_logging()
    asyncio.run(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
