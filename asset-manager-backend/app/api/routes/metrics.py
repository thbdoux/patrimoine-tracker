from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services import analytics_service as svc

router = APIRouter()


@router.get("/performance")
async def performance(db: Annotated[AsyncSession, Depends(get_db)]):
    """ATH, max drawdown, volatilité annualisée (30j et 1an)."""
    return await svc.get_performance_metrics(db)


@router.get("/sync")
async def sync_status(db: Annotated[AsyncSession, Depends(get_db)]):
    """Statut de la dernière sync par source (powens, binance)."""
    return await svc.get_sync_status(db)
