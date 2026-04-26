"""Ollama AI enrichment service.

Connects to an Ollama instance (local or cloud) via OLLAMA_BASE_URL.
All public functions degrade gracefully when Ollama is unreachable.
"""
import json
import logging

import ollama

from app.core.config import Settings

logger = logging.getLogger(__name__)


def get_client() -> ollama.Client:
    return ollama.Client(host=Settings().ollama_base_url)


def enrich_book(title: str, authors: list[str], description: str | None) -> dict:
    """Ask Ollama to return a JSON object with ai_summary, suggested_tags, and themes.

    Returns a dict with null/empty values if Ollama is unavailable.
    """
    settings = Settings()
    author_str = ", ".join(authors) if authors else "Unknown"
    desc_block = f"\nDescription: {description}" if description else ""

    prompt = (
        f"You are a book metadata assistant. Analyze the following book and respond ONLY with "
        f"a valid JSON object — no markdown, no extra text.\n\n"
        f"Book: {title}\nAuthor(s): {author_str}{desc_block}\n\n"
        f'Return exactly this shape:\n'
        f'{{"ai_summary": "<2-3 sentence summary>", '
        f'"suggested_tags": ["<tag1>", "<tag2>", "..."], '
        f'"themes": ["<theme1>", "<theme2>", "..."]}}'
    )

    client = get_client()
    try:
        response = client.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
        return json.loads(response.message.content)
    except ollama.ResponseError as exc:
        logger.warning("Ollama ResponseError during enrichment: %s", exc)
        raise
    except Exception as exc:
        logger.warning("Ollama unavailable during enrichment: %s", exc)
        raise


def check_ollama_health() -> bool:
    """Return True if Ollama is reachable, False otherwise."""
    try:
        client = get_client()
        client.list()
        return True
    except Exception:
        return False
