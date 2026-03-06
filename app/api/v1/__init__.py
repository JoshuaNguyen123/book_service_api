from fastapi import APIRouter

from app.api.v1 import books, health

api_router = APIRouter(prefix="/v1", tags=["v1"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(books.router, prefix="/books", tags=["books"])
