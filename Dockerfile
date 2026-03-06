FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app/ app/
COPY scripts/ scripts/

RUN pip install --no-cache-dir . && \
    adduser --disabled-password --gecos "" appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

ENV DATABASE_URL=sqlite:///./data/app.db
EXPOSE 8000

# Production: single worker; use multiple workers behind a reverse proxy in production if needed
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
