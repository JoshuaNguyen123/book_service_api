from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/health", response_model=dict)
def health(db: Session = Depends(get_db)):
    """Health check: verify the app can talk to the database."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail={"code": "service_unavailable", "message": "Database is unavailable", "details": {}},
        )
    return {"status": "ok"}
