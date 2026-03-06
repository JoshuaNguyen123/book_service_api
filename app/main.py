"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import Settings
from app.db.session import init_db

logger = logging.getLogger(__name__)


def _error_response(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup."""
    init_db()
    yield


async def http_exception_handler(request: Request, exc):
    """Format HTTPException as spec: { \"error\": { \"code\", \"message\", \"details\" } }."""
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        body = {"error": {"code": detail["code"], "message": detail["message"], "details": detail.get("details", {})}}
    else:
        code = {404: "not_found", 409: "conflict", 422: "validation_error"}.get(exc.status_code, "error")
        body = _error_response(code, str(detail) if not isinstance(detail, dict) else "Validation or conflict error", detail if isinstance(detail, dict) else None)
    return JSONResponse(status_code=exc.status_code, content=body)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format 422 validation errors as spec."""
    details = {"errors": jsonable_encoder(exc.errors())}
    return JSONResponse(status_code=422, content=_error_response("validation_error", "Request validation failed", details))


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Return standard error format for 500; log full traceback server-side."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content=_error_response("internal_error", "An unexpected error occurred", {}),
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Book API", version="1.0.0", lifespan=lifespan)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    settings = Settings()
    if settings.cors_origins:
        from fastapi.middleware.cors import CORSMiddleware
        origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
    app.include_router(api_router)
    return app


app = create_app()
