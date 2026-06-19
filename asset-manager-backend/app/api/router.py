from fastapi import APIRouter

from app.api.routes import accounts, enablebanking, history, metrics, overview

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(overview.router, tags=["overview"])
api_router.include_router(history.router, tags=["history"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(
    enablebanking.router, prefix="/connect/enablebanking", tags=["enablebanking"]
)
