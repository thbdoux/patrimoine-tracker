from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services import analytics_service as svc

router = APIRouter()

PeriodType = Literal["7D", "1M", "3M", "6M", "1Y", "ALL"]


@router.get("")
async def list_accounts(db: Annotated[AsyncSession, Depends(get_db)]):
    """Liste des comptes actifs avec leur dernier snapshot et variation 24h."""
    return await svc.get_accounts_with_latest(db)


@router.get("/{account_id}/history")
async def account_history(
    account_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    period: PeriodType = Query("3M"),
):
    """Historique d'un compte individuel."""
    return await svc.get_account_history(db, account_id=account_id, period=period)
