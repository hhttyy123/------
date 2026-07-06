"""API v1 路由聚合"""

from fastapi import APIRouter

from app.api.v1.upload import router as upload_router
from app.api.v1.preview import router as preview_router
from app.api.v1.analyze import router as analyze_router
from app.api.v1.import_ import router as import_router
from app.api.v1.import_chat import router as import_chat_router
from app.api.v1.modules import router as modules_router
from app.api.v1.datasets import router as datasets_router

router = APIRouter(prefix="/api/v1")
router.include_router(upload_router, tags=["upload"])
router.include_router(preview_router, tags=["preview"])
router.include_router(analyze_router, tags=["analyze"])
router.include_router(import_router, tags=["import"])
router.include_router(import_chat_router, tags=["import-chat"])
router.include_router(modules_router, tags=["modules"])
router.include_router(datasets_router, tags=["datasets"])
