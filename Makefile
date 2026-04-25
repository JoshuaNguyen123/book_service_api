.PHONY: install test lint format run docker-build docker-run seed migrate

install:
	pip install -e ".[dev]"

test:
	pytest --cov=app --cov-report=term-missing

lint:
	ruff check .

format:
	ruff format .

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t book-api .

docker-run:
	docker compose up

seed:
	python scripts/seed_books.py

migrate:
	alembic upgrade head
