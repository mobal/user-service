from fastapi import APIRouter

from app.api.v1.routers import roles_router, users_router

router = APIRouter(prefix="/api/v1", tags=["api"])
router.include_router(users_router.router, tags=["users"])
router.include_router(roles_router.router, tags=["roles"])
