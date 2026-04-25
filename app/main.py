"""FastAPI application entry point."""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1 import api_router as v1_router
from app.api.v2 import api_router as v2_router
from app.core.config import Settings
from app.db.session import init_db

logger = logging.getLogger(__name__)


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info("%s %s %s %dms", request.method, request.url.path, response.status_code, duration_ms)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


def _error_response(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup."""
    init_db()
    yield


async def http_exception_handler(request: Request, exc: HTTPException):
    """Format HTTPException as spec: { \"error\": { \"code\", \"message\", \"details\" } }."""
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        body = {"error": {"code": detail["code"], "message": detail["message"], "details": detail.get("details", {})}}
    else:
        code = {404: "not_found", 409: "conflict", 422: "validation_error"}.get(exc.status_code, "error")
        msg = str(detail) if not isinstance(detail, dict) else "Validation or conflict error"
        body = _error_response(code, msg, detail if isinstance(detail, dict) else None)
    return JSONResponse(status_code=exc.status_code, content=body)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format 422 validation errors as spec."""
    details = {"errors": jsonable_encoder(exc.errors())}
    return JSONResponse(
        status_code=422, content=_error_response("validation_error", "Request validation failed", details)
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Return standard error format for 500; log full traceback server-side."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content=_error_response("internal_error", "An unexpected error occurred", {}),
    )


def create_app() -> FastAPI:
    settings = Settings()
    configure_logging(settings)

    app = FastAPI(
        title="Book API",
        version=settings.app_version,
        description=(
            "A production-ready REST API for managing books.\n\n"
            "**v1** — stable CRUD with search, filtering, and pagination.\n\n"
            "**v2** — frontier capabilities: Ollama AI enrichment, web crawling, "
            "ISBN lookup, web search, and bulk operations."
        ),
        contact={"name": "Book API", "url": "https://github.com/joshuanguyen123/book_service_api"},
        license_info={"name": "MIT"},
        openapi_tags=[
            {"name": "health", "description": "Service health and readiness checks"},
            {"name": "books-v1", "description": "v1 — stable CRUD, search, filtering, pagination"},
            {"name": "books-v2", "description": "v2 — AI enrichment, web search, ISBN lookup, bulk ops"},
        ],
        lifespan=lifespan,
    )

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    if settings.cors_origins:
        from fastapi.middleware.cors import CORSMiddleware
        origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

    app.include_router(v1_router)
    app.include_router(v2_router)
    return app


app = create_app()
