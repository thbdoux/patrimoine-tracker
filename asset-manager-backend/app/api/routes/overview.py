from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services import analytics_service as svc

router = APIRouter()


@router.get("/overview")
async def overview(db: Annotated[AsyncSession, Depends(get_db)]):
    """Total patrimoine + variations 1j/7j/30j/1an/inception."""
    return await svc.get_overview(db)


@router.get("/allocation")
async def allocation(db: Annotated[AsyncSession, Depends(get_db)]):
    """Répartition actuelle par type de compte et par source."""
    return await svc.get_allocation(db)
