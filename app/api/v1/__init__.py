from fastapi import APIRouter

from app.api.v1 import books, health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/v1")
api_router.include_router(books.router, prefix="/v1/books")
