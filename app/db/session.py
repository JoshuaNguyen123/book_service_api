"""Database engine and session factory."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base


def get_engine():
    """Create engine from settings. SQLite needs check_same_thread=False for FastAPI."""
    settings = Settings()
    connect_args = {} if "sqlite" not in settings.database_url else {"check_same_thread": False}
    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=False,
    )


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables (MVP: no Alembic). Ensure data dir exists for SQLite file."""
    from app.core.config import Settings
    url = Settings().database_url
    if url.startswith("sqlite:///") and "/" in url.replace("sqlite:///", ""):
        from pathlib import Path
        path = Path(url.replace("sqlite:///", "", 1))
        path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
