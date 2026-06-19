from datetime import datetime, timedelta, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.connectors.enablebanking.repository import parse_valid_until, upsert_session
from app.connectors.enablebanking.service import build_client

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/start")
async def start_consent(
    aspsp: Annotated[str, Query(description="Nom exact de l'ASPSP, ex: 'Trade Republic'")],
    country: Annotated[str, Query(min_length=2, max_length=2, description="Code pays ISO, ex: DE")],
    days: Annotated[int, Query(ge=1, le=180, description="Validité du consentement en jours")] = 90,
):
    """
    Démarre le flux de consentement PSD2 et redirige le navigateur vers la banque.
    Après consentement, l'utilisateur revient sur /callback.
    """
    valid_until = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    async with build_client() as client:
        try:
            auth = await client.start_authorization(
                aspsp_name=aspsp,
                aspsp_country=country,
                redirect_url=settings.enablebanking_redirect_url,
                valid_until=valid_until,
                state=f"{aspsp}|{country}",
            )
        except Exception as e:
            logger.error("enablebanking_start_failed", aspsp=aspsp, error=str(e))
            raise HTTPException(status_code=502, detail=f"Enable Banking start failed: {e}") from e

    url = auth.get("url")
    if not url:
        raise HTTPException(status_code=502, detail="Enable Banking n'a pas renvoyé d'URL de consentement")
    return RedirectResponse(url)


@router.get("/callback")
async def consent_callback(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: Annotated[str, Query(description="Code de redirection renvoyé par la banque")],
    state: Annotated[str, Query()] = "",
):
    """
    Callback du flux de consentement : échange le code contre une session
    et la persiste en base.
    """
    async with build_client() as client:
        try:
            session = await client.create_session(code)
        except Exception as e:
            logger.error("enablebanking_callback_failed", error=str(e))
            raise HTTPException(status_code=502, detail=f"Enable Banking session creation failed: {e}") from e

    session_id = session.get("session_id")
    if not session_id:
        raise HTTPException(status_code=502, detail="Enable Banking n'a pas renvoyé de session_id")

    aspsp = session.get("aspsp") or {}
    # Fallback sur le state (aspsp|country) si l'ASPSP n'est pas dans la réponse
    state_name, _, state_country = state.partition("|")
    aspsp_name = aspsp.get("name") or state_name or "unknown"
    aspsp_country = aspsp.get("country") or state_country or ""
    valid_until = parse_valid_until((session.get("access") or {}).get("valid_until"))

    row = await upsert_session(
        db,
        session_id=session_id,
        aspsp_name=aspsp_name,
        aspsp_country=aspsp_country,
        valid_until=valid_until,
        metadata={"accounts": session.get("accounts", [])},
    )
    logger.info("enablebanking_session_saved", aspsp=aspsp_name, session_id=session_id)

    return {
        "status": "ok",
        "aspsp": aspsp_name,
        "session_id": session_id,
        "valid_until": row.valid_until.isoformat() if row.valid_until else None,
        "accounts": len(session.get("accounts", [])),
    }
