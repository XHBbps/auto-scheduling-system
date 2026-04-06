from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


async def check_db_health() -> bool:
    """Execute a lightweight query to verify database connectivity."""
    from sqlalchemy import text

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
