"""
Application entrypoint.

Layered architecture (spec Section 130):

    UI -> API -> Domain (accounting/tax/bir engines) -> Database

This module wires the FastAPI app, CORS, security/logging/rate-limit
middleware, and the versioned API router. Accounting/tax logic never
lives here -- see app/accounting, app/tax, app/bir.
"""
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.config import get_settings
from app.core.logging_config import configure_logging
from app.core.rate_limit import RateLimitMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.base import Base, engine

# Import models so metadata is registered before create_all runs.
from app.models import (  # noqa: F401
    account,
    bank,
    bank_reconciliation,
    budget,
    business,
    cash_disbursement,
    cash_receipt,
    customer,
    depreciation_entry,
    fixed_asset,
    inventory_item,
    journal,
    period,
    purchase,
    refresh_token,
    sales,
    stock_movement,
    tax_rule,
    user,
    vendor,
    withholding_certificate,
)

configure_logging()
logger = logging.getLogger("app")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fast local bootstrap only. In production, Alembic migrations
    # (backend/migrations) are the source of truth for schema changes
    # -- create_all here would silently mask a missing/failed
    # migration in a shared environment, so it's skipped entirely
    # when ENVIRONMENT=production (see app/config.py::is_production).
    if not settings.is_production:
        Base.metadata.create_all(bind=engine)
    else:
        logger.info("Production mode: skipping create_all; relying on Alembic migrations.")
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Designed to support Philippine BIR requirements. "
        "Certification or registration requirements remain subject to "
        "applicable BIR procedures and approvals."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
# Rate limiting is enabled only in production. In development/test,
# the FastAPI `app` object (and therefore this middleware's in-memory
# counters) persists for the life of the process -- across an entire
# test suite run, not per-request -- so enabling it unconditionally
# here would make automated tests flaky depending on run order/count
# rather than protecting anything real in those environments.
if settings.is_production:
    app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)


@app.middleware("http")
async def request_id_and_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} [{request_id}]")
    return response


# Global exception handlers: every error response, expected or not,
# comes back as consistent JSON ({"detail": "..."}) rather than
# leaking a stack trace or an inconsistent shape to the client.
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again or contact support."},
    )


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "app": settings.app_name}


# Serve the built frontend (frontend/dist, copied to app/static by
# scripts/build_exe.bat) when it exists -- lets a single backend
# process serve both the API and the UI, which is what the packaged
# .exe does. In normal `npm run dev` local development this directory
# doesn't exist, so this mount is simply skipped and the Vite dev
# server (with its /api proxy) is used instead, exactly as before.
# Mounted LAST so it never shadows /api/v1/* or /health.
_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="frontend")
    logger.info(f"Serving built frontend from {_static_dir}")
