import logging
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.cache import close_redis
from app.common.middleware import RequestLoggingMiddleware
from app.monitoring.metrics import setup_metrics
from app.monitoring.tracing import setup_tracing
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.doctors.router import router as doctors_router
from app.modules.bookings.router import router as bookings_router
from app.modules.consultations.router import router as consultations_router
from app.modules.payments.router import router as payments_router
from app.modules.prescriptions.router import router as prescriptions_router
from app.modules.search.router import router as search_router
from app.modules.analytics.router import router as analytics_router
from app.modules.audit.router import router as audit_router

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
    yield
    await close_redis()


app = FastAPI(
    title="Amrutam Telemedicine API",
    version="0.1.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

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
