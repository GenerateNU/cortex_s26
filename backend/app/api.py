from app.core.supabase import get_async_supabase
from app.routes.classification_routes import router as classification_router
from app.routes.migration_routes import router as migration_router
from app.routes.pattern_recognition_routes import router as pattern_recognition_router
from app.routes.preprocess_routes import router as preprocess_router
from app.routes.search_routes import router as search_router
from fastapi import APIRouter, Depends
from supabase._async.client import AsyncClient

from app.routes.documents import router as documents_router

api_router = APIRouter(prefix="/api")


@api_router.get("/health")
async def health_check(supabase: AsyncClient = Depends(get_async_supabase)):
    try:
        await supabase.table("cortex_documents").select("count", count="exact").execute()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


api_router.include_router(preprocess_router)
api_router.include_router(search_router)
api_router.include_router(classification_router)
api_router.include_router(migration_router)
api_router.include_router(pattern_recognition_router)
api_router.include_router(documents_router)
