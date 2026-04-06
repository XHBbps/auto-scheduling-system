import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.common.exceptions import BizException
from app.config import settings
from app.database import engine
from app.models import Base
from app.openapi import OPENAPI_DESCRIPTION, OPENAPI_TAGS, build_custom_openapi

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.common.logging_setup import configure_logging

    configure_logging()

    if settings.database_auto_create_all:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.warning("DATABASE_AUTO_CREATE_ALL=true, create_all executed on startup.")
        except Exception as exc:
            logger.warning(
                "DATABASE_AUTO_CREATE_ALL=true, create_all skipped (tables likely exist via Alembic): %s", exc
            )
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

from app.routers.auth_router import limiter as auth_limiter  # noqa: E402

app.state.limiter = auth_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Cookie", "X-Requested-With"],
)

from app.common.request_id_middleware import RequestIdMiddleware  # noqa: E402

app.add_middleware(RequestIdMiddleware)

import time  # noqa: E402

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint  # noqa: E402
from starlette.requests import Request as StarletteRequest  # noqa: E402
from starlette.responses import Response as StarletteResponse  # noqa: E402


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next: RequestResponseEndpoint) -> StarletteResponse:
        if request.url.path in ("/health", "/metrics"):
            return await call_next(request)
        from app.common.metrics import http_request_duration_seconds, http_requests_total

        method = request.method
        path = request.url.path
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        status = str(response.status_code)
        http_requests_total.labels(method=method, endpoint=path, status_code=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=path).observe(duration)
        return response


app.add_middleware(MetricsMiddleware)


@app.exception_handler(BizException)
async def biz_exception_handler(request: Request, exc: BizException):
    return JSONResponse(
        status_code=200,
        content={"code": int(exc.code), "message": exc.message, "data": None},
    )


@app.get("/health")
async def health():
    from app.database import check_db_health

    db_ok = await check_db_health()
    return {
        "status": "ok" if db_ok else "degraded",
        "version": "0.1.0",
        "db": "ok" if db_ok else "error",
    }


@app.get("/metrics", include_in_schema=False)
async def metrics():
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    from starlette.responses import Response as StarletteResponse

    from app.common.metrics import app_info, background_task_pending, db_pool_checked_out, db_pool_size

    app_info.info({"version": "0.1.0", "env": settings.app_env})

    pool = engine.pool
    db_pool_size.set(pool.size())
    db_pool_checked_out.set(pool.checkedout())

    try:
        from sqlalchemy import func, select

        from app.database import async_session_factory
        from app.models.background_task import BackgroundTask

        async with async_session_factory() as session:
            result = await session.execute(
                select(func.count()).select_from(BackgroundTask).where(BackgroundTask.status == "pending")
            )
            pending_count = result.scalar() or 0
            background_task_pending.set(pending_count)
    except Exception:
        pass  # metrics collection should never break the endpoint

    return StarletteResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


from app.routers import (  # noqa: E402
    admin_assembly_time_router,
    admin_issue_router,
    admin_machine_cycle_router,
    admin_part_cycle_router,
    admin_schedule_router,
    admin_sync_log_router,
    admin_sync_router,
    admin_user_router,
    admin_work_calendar_router,
    auth_router,
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
