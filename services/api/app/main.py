import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.common.exceptions import BizException
from app.config import settings
from app.openapi import OPENAPI_DESCRIPTION, OPENAPI_TAGS, build_custom_openapi
from app.database import engine
from app.models import Base  # noqa: F401 - import all models so Base.metadata is complete

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_auto_create_all:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.warning("DATABASE_AUTO_CREATE_ALL=true, create_all executed on startup.")
        except Exception as exc:
            logger.warning("DATABASE_AUTO_CREATE_ALL=true, create_all skipped (tables likely exist via Alembic): %s", exc)
    else:
        logger.info("Startup skipped create_all; expect schema to be managed by Alembic migrations.")

    # Seed default roles/permissions/admin user on startup (once)
    try:
        from app.database import async_session_factory
        from app.services.user_auth_service import ensure_identity_seeded
        async with async_session_factory() as session:
            await ensure_identity_seeded(session)
            await session.commit()
        logger.info("Identity seed check completed on startup.")
    except Exception as exc:
        logger.warning("Identity seed on startup skipped: %s", exc)

    yield
    await engine.dispose()


_is_production = settings.app_env.lower() in {"production", "prod"}

app = FastAPI(
    title="自动排产系统 API",
    version="0.1.0",
    summary="自动排产系统后端接口文档",
    description=OPENAPI_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    swagger_ui_parameters={
        "displayRequestDuration": True,
        "docExpansion": "list",
        "defaultModelsExpandDepth": 2,
    },
    lifespan=lifespan,
)

from app.routers.auth_router import limiter as auth_limiter
app.state.limiter = auth_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BizException)
async def biz_exception_handler(request: Request, exc: BizException):
    return JSONResponse(
        status_code=200,
        content={"code": int(exc.code), "message": exc.message, "data": None},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


from app.routers import (  # noqa: E402
    admin_assembly_time_router,
    admin_user_router,
    auth_router,
    admin_issue_router,
    admin_machine_cycle_router,
    admin_part_cycle_router,
    admin_schedule_router,
    admin_sync_log_router,
    admin_sync_router,
    admin_work_calendar_router,
    data_source_bom_router,
    data_source_machine_cycle_history_router,
    data_source_production_order_router,
    data_source_sales_plan_router,
    issue_query_router,
    schedule_export_router,
    schedule_query_router,
)

app.include_router(schedule_query_router.router)
app.include_router(issue_query_router.router)
app.include_router(auth_router.router)
app.include_router(schedule_export_router.router)
app.include_router(admin_sync_router.router)
app.include_router(admin_schedule_router.router)
app.include_router(admin_assembly_time_router.router)
app.include_router(admin_work_calendar_router.router)
app.include_router(admin_issue_router.router)
app.include_router(admin_machine_cycle_router.router)
app.include_router(admin_part_cycle_router.router)
app.include_router(admin_sync_log_router.router)
app.include_router(admin_user_router.router)
app.include_router(data_source_sales_plan_router.router)
app.include_router(data_source_bom_router.router)
app.include_router(data_source_production_order_router.router)
app.include_router(data_source_machine_cycle_history_router.router)


app.openapi = build_custom_openapi(app)
