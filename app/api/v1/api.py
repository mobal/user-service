from fastapi import APIRouter

from app.api.v1.routers import users_router

router = APIRouter(prefix="/v1", tags=["api"])
router.include_router(users_router.router, tags=["users"])
