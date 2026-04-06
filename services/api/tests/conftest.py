import pytest_asyncio
from sqlalchemy import JSON, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        pass

    async with engine.begin() as conn:
        for table in Base.metadata.tables.values():
            for column in table.columns:
                if isinstance(column.type, JSONB):
                    column.type = JSON()
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def app_client(db_session):
    from httpx import ASGITransport, AsyncClient

    from app.config import settings
    from app.database import get_session
    from app.main import app
    from app.routers.auth_router import limiter
    from app.services.user_auth_service import ensure_identity_seeded

    async def override_get_session():
        yield db_session

    original_username = settings.bootstrap_admin_username
    original_display_name = settings.bootstrap_admin_display_name
    original_password = settings.bootstrap_admin_password
    original_cookie_secure = settings.user_session_cookie_secure

    settings.bootstrap_admin_username = "admin"
    settings.bootstrap_admin_display_name = "系统管理员"
    settings.bootstrap_admin_password = "Admin123456"
    settings.user_session_cookie_secure = False
    limiter.enabled = False
    app.dependency_overrides[get_session] = override_get_session

    # Seed admin user (lifespan doesn't run in test ASGITransport)
    await ensure_identity_seeded(db_session)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post(
            "/api/auth/login",
            json={"username": settings.bootstrap_admin_username, "password": settings.bootstrap_admin_password},
        )
        assert login_resp.status_code == 200
        yield client

    limiter.enabled = True
    settings.bootstrap_admin_username = original_username
    settings.bootstrap_admin_display_name = original_display_name
    settings.bootstrap_admin_password = original_password
    settings.user_session_cookie_secure = original_cookie_secure
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def app_client_no_admin_token(db_session):
    from httpx import ASGITransport, AsyncClient

    from app.config import settings
    from app.database import get_session
    from app.main import app
    from app.routers.auth_router import limiter

    async def override_get_session():
        yield db_session

    original_username = settings.bootstrap_admin_username
    original_display_name = settings.bootstrap_admin_display_name
    original_password = settings.bootstrap_admin_password
    original_cookie_secure = settings.user_session_cookie_secure

    settings.bootstrap_admin_username = "admin"
    settings.bootstrap_admin_display_name = "系统管理员"
    settings.bootstrap_admin_password = "Admin123456"
    settings.user_session_cookie_secure = False
    limiter.enabled = False
    app.dependency_overrides[get_session] = override_get_session

    # Seed admin user (lifespan doesn't run in test ASGITransport)
    from app.services.user_auth_service import ensure_identity_seeded

    await ensure_identity_seeded(db_session)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    limiter.enabled = True
    settings.bootstrap_admin_username = original_username
    settings.bootstrap_admin_display_name = original_display_name
    settings.bootstrap_admin_password = original_password
    settings.user_session_cookie_secure = original_cookie_secure
    app.dependency_overrides.clear()
