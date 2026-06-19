#!/usr/bin/env python3
"""
Bootstrap manuel du consentement Enable Banking (Phase 0).

Mirroir de scripts/powens-connect.sh : lance le flux de consentement PSD2,
ouvre l'URL de la banque, échange le code de redirection contre une session,
et affiche le session_id à coller dans ENABLEBANKING_SESSION_ID.

Usage :
    python scripts/enablebanking-connect.py --country DE
    python scripts/enablebanking-connect.py --aspsp "Trade Republic" --country DE

Prérequis (.env) : ENABLEBANKING_APP_ID, ENABLEBANKING_PRIVATE_KEY_PATH
(ou ENABLEBANKING_PRIVATE_KEY), ENABLEBANKING_REDIRECT_URL.
"""
import argparse
import asyncio
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Permet d'importer `app` quand le script est lancé depuis n'importe où
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.connectors.enablebanking.client import EnableBankingClient  # noqa: E402


def _build_client() -> EnableBankingClient:
    private_key = EnableBankingClient.load_private_key(
        inline=settings.enablebanking_private_key,
        path=settings.enablebanking_private_key_path,
    )
    return EnableBankingClient(
        app_id=settings.enablebanking_app_id,
        private_key_pem=private_key,
        base_url=settings.enablebanking_base_url,
    )


def _extract_code(raw: str) -> str:
    """Accepte soit le code brut, soit l'URL de redirection complète collée."""
    raw = raw.strip()
    if raw.startswith("http"):
        qs = parse_qs(urlparse(raw).query)
        if "code" not in qs:
            raise SystemExit("Aucun paramètre `code` dans l'URL collée.")
        return qs["code"][0]
    return raw


async def main(aspsp: str | None, country: str, days: int) -> None:
    async with _build_client() as client:
        # 1. Sanity check de la signature JWT
        app = await client.get_application()
        print(f"✓ Application OK : {app.get('name', settings.enablebanking_app_id)}")
        print(f"  Redirect URLs enregistrées : {app.get('redirect_urls')}\n")

        # 2. Si l'ASPSP n'est pas fourni, lister les banques du pays
        if not aspsp:
            aspsps = await client.get_aspsps(country=country)
            print(f"Banques disponibles ({country}) :")
            for a in aspsps:
                print(f"  - {a.get('name')}  ({a.get('country')})")
            print("\nRelance avec --aspsp \"<nom exact>\".")
            return

        # 3. Démarrer l'autorisation
        valid_until = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        auth = await client.start_authorization(
            aspsp_name=aspsp,
            aspsp_country=country,
            redirect_url=settings.enablebanking_redirect_url,
            valid_until=valid_until,
            state="bootstrap",
        )
        url = auth.get("url")
        print(f"Authorization ID : {auth.get('authorization_id')}")
        print("\nOuvre cette URL et donne ton consentement :\n")
        print(f"  {url}\n")
        try:
            webbrowser.open(url)
        except Exception:
            pass

        # 4. Récupérer le code après redirection
        raw = input("Colle l'URL de redirection complète (ou juste le `code`) : ")
        code = _extract_code(raw)

        # 5. Échanger le code contre une session
        session = await client.create_session(code)
        session_id = session.get("session_id")
        accounts = session.get("accounts", [])
        print("\n✓ Session créée.")
        print(f"\n  ENABLEBANKING_SESSION_ID={session_id}\n")
        print(f"  {len(accounts)} compte(s) trouvé(s) :")
        for a in accounts:
            if isinstance(a, dict):
                print(f"    - uid={a.get('uid')} | {a.get('name') or a.get('product')} "
                      f"| type={a.get('cash_account_type')} | {a.get('currency')}")
            else:
                print(f"    - uid={a}")
        print("\n→ Vérifie si le détail des TITRES (positions) apparaît : c'est le critère Phase 0.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap consentement Enable Banking")
    parser.add_argument("--aspsp", help="Nom exact de l'ASPSP (ex: 'Trade Republic'). Sans ça, liste les banques.")
    parser.add_argument("--country", default="DE", help="Code pays ISO de l'ASPSP (défaut: DE)")
    parser.add_argument("--days", type=int, default=90, help="Validité du consentement en jours (défaut: 90)")
    args = parser.parse_args()
    asyncio.run(main(args.aspsp, args.country, args.days))
