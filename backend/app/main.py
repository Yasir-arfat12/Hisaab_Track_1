from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.csrf import CSRFMiddleware
from app.config import settings
from app.database import async_session_factory, engine, init_db
from app.mcp_server import mcp_asgi_app, mcp_http_app
from app.routers.auth import router as auth_router
from app.routers.bank_credits import router as credits_router
from app.routers.dashboard import router as dashboard_router
from app.routers.demo import router as demo_router
from app.routers.dossier import router as dossier_router
from app.routers.escalation import router as escalation_router
from app.routers.gmail import router as gmail_router
from app.routers.health import router as health_router
from app.routers.jobs import router as jobs_router
from app.routers.merchants import router as merchants_router
from app.routers.promises import router as promises_router
from app.routers.verify import router as verify_router
from app.services.purge_service import purge_expired_cache_and_idempotency
from app.utils.exceptions import register_exception_handlers
from app.utils.logging import RequestIdMiddleware, configure_logging
from app.utils.rate_limit import RateLimitMiddleware, SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.ENVIRONMENT, settings.LOG_LEVEL)
    if settings.ENVIRONMENT == "dev":
        await init_db()
    async with async_session_factory() as db:
        await purge_expired_cache_and_idempotency(db)
    async with mcp_http_app.lifespan(app):
        yield
    await engine.dispose()


def create_app() -> FastAPI:
    configure_logging(settings.ENVIRONMENT, settings.LOG_LEVEL)
    application = FastAPI(
        title=settings.APP_TITLE,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "X-CSRF-Token",
            "Idempotency-Key",
            "X-Request-ID",
        ],
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(CSRFMiddleware)
    application.add_middleware(RequestIdMiddleware)

    register_exception_handlers(application)
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(gmail_router, prefix="/api/v1")
    application.include_router(jobs_router, prefix="/api/v1")
    application.include_router(dashboard_router, prefix="/api/v1")
    application.include_router(promises_router, prefix="/api/v1")
    application.include_router(credits_router, prefix="/api/v1")
    application.include_router(verify_router, prefix="/api/v1")
    application.include_router(escalation_router, prefix="/api/v1")
    application.include_router(dossier_router, prefix="/api/v1")
    application.include_router(merchants_router, prefix="/api/v1")
    application.include_router(demo_router, prefix="/api/v1")
    application.include_router(health_router, prefix="/api/v1")
    application.mount("/mcp", mcp_asgi_app)

    return application


app = create_app()
