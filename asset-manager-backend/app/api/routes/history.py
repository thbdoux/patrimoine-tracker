from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services import analytics_service as svc

router = APIRouter()

PeriodType = Literal["7D", "1M", "3M", "6M", "1Y", "ALL"]
GranularityType = Literal["1H", "6H", "1D", "1W", "1M"]


@router.get("/history")
async def patrimoine_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    period: PeriodType = Query("1Y"),
    granularity: GranularityType = Query("1D"),
):
    """Série temporelle du patrimoine total (avec forward-fill par compte)."""
    return await svc.get_patrimoine_history(db, period=period, granularity=granularity)


@router.get("/history/stacked")
async def stacked_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    period: PeriodType = Query("1Y"),
    granularity: GranularityType = Query("1D"),
):
    """Série temporelle décomposée par type de compte (pour stacked area chart)."""
    return await svc.get_stacked_history(db, period=period, granularity=granularity)


@router.get("/history/returns")
async def return_distribution(
    db: Annotated[AsyncSession, Depends(get_db)],
    period: PeriodType = Query("1Y"),
):
    """Rendements journaliers (pour histogramme de distribution)."""
    return await svc.get_return_distribution(db, period=period)
