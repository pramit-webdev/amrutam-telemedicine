import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

import app.models  # noqa: F401 — load all models for SQLAlchemy registry
from app.common.middleware import RequestLoggingMiddleware
from app.common.rate_limit import rate_limiter
from app.core.cache import close_redis
from app.core.config import get_settings
from app.modules.analytics.router import router as analytics_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.bookings.router import router as bookings_router
from app.modules.consultations.router import router as consultations_router
from app.modules.doctors.router import router as doctors_router
from app.modules.payments.router import router as payments_router
from app.modules.prescriptions.router import router as prescriptions_router
from app.modules.search.router import router as search_router
from app.modules.users.router import router as users_router
from app.monitoring.metrics import setup_metrics
from app.monitoring.tracing import setup_tracing

settings = get_settings()

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.environment == "development"
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.log_level.upper(), logging.INFO)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment == "production":
        from app.core.base import Base
        from app.core.database import engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await close_redis()


app = FastAPI(
    title="Amrutam Telemedicine API",
    version="0.1.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan,
)

app.state.limiter = rate_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(doctors_router)
app.include_router(bookings_router)
app.include_router(consultations_router)
app.include_router(payments_router)
app.include_router(prescriptions_router)
app.include_router(search_router)
app.include_router(analytics_router)
app.include_router(audit_router)

if settings.enable_metrics:
    setup_metrics(app)

if settings.enable_tracing:
    setup_tracing(app)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "amrutam-telemedicine"}


@app.get("/db-check")
async def db_check():
    from sqlalchemy import text

    from app.core.database import engine
    try:
        async with engine.connect() as conn:
            r = await conn.execute(text("SELECT 1"))
            return {"db": "ok", "result": r.scalar()}
    except Exception as e:
        return {"db": "error", "error": str(e), "type": type(e).__name__}
