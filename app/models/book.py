"""Book SQLAlchemy model."""
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, String, Text, Integer
from sqlalchemy.dialects.sqlite import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    authors: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    isbn: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    published_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)

    def get_authors_list(self) -> list[str]:
        if not self.authors:
            return []
        try:
            return json.loads(self.authors)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_authors_list(self, value: list[str]) -> None:
        self.authors = json.dumps(value) if value else "[]"

    def get_tags_list(self) -> list[str]:
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tags_list(self, value: list[str]) -> None:
        self.tags = json.dumps(value) if value else "[]"
