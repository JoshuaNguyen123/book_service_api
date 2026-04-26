"""v2 health endpoint — includes Ollama and uptime status."""
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db
from app.services.ollama_client import check_ollama_health

router = APIRouter()

_START_TIME = time.monotonic()


@router.get(
    "/v2/health",
    tags=["health"],
    summary="v2 health check",
    description=(
        "Extended health check. Reports database connectivity, Ollama reachability, "
        "app version, and uptime."
    ),
    response_model=dict,
)
def health_v2(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail={"code": "service_unavailable", "message": "Database is unavailable", "details": {}},
        )

    ollama_ok = check_ollama_health()
    settings = Settings()

    return {
        "status": "ok",
        "version": settings.app_version,
        "database": db_status,
        "ollama": "ok" if ollama_ok else "unavailable",
        "ollama_model": settings.ollama_model,
        "uptime_seconds": round(time.monotonic() - _START_TIME, 1),
    }
