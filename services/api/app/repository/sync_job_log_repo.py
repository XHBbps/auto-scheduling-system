from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_job_log import SyncJobLog
from app.repository.base import BaseRepository


class SyncJobLogRepo(BaseRepository[SyncJobLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, SyncJobLog)
