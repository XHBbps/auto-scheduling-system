from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import async_session_factory as default_async_session_factory
from app.sync.bom_backfill_queue_service import (
    AutoBomBackfillResult,
    BomBackfillQueueConsumeResult,
    BomBackfillQueueService,
)


class AutoBomBackfillService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        self.session_factory = session_factory or default_async_session_factory
        self.queue_service = BomBackfillQueueService(self.session_factory)

    async def run(
        self,
        *,
        source: str,
        reason: str,
        sap_bom_base_url: str,
        order_line_ids: list[int] | None = None,
    ) -> AutoBomBackfillResult:
        return await self.queue_service.enqueue_candidates(
            source=source,
            reason=reason,
            order_line_ids=order_line_ids,
        )

    async def consume(
        self,
        *,
        source: str,
        reason: str,
        sap_bom_base_url: str,
        existing_job_id: int | None = None,
    ) -> BomBackfillQueueConsumeResult:
        return await self.queue_service.consume_queue(
            source=source,
            reason=reason,
            sap_bom_base_url=sap_bom_base_url,
            existing_job_id=existing_job_id,
        )
