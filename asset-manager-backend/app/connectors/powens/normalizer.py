from decimal import Decimal
from typing import Optional

from app.connectors.base import NormalizedAccount

SOURCE = "powens"

POWENS_TYPE_MAP = {
    "checking": "checking",
    "savings": "savings",
    "loan": "loan",
    "market": "brokerage",
    "pea": "pea",
    "employee-savings": "pee",
    "retirement": "per",
    "life-insurance": "life_insurance",
    "lifeinsurance": "life_insurance",
    "capitalisation": "life_insurance",
    "article83": "per",
    "perco": "pee",
    "perp": "per",
    "madelin": "per",
}


def _map_type(powens_type: str, name: str = "") -> str:
    t = powens_type.lower().strip()
    # market → pea si "PEA" dans le nom (prioritaire sur le map générique)
    if t == "market" and "PEA" in name.upper():
        return "pea"
    if t in POWENS_TYPE_MAP:
        return POWENS_TYPE_MAP[t]
    return "other"


def normalize_bank_account(account: dict) -> NormalizedAccount:
    balance = Decimal(str(account.get("balance", 0)))
    currency = account.get("currency", {})
    currency_id = currency.get("id", "EUR") if isinstance(currency, dict) else str(currency)

    return NormalizedAccount(
        external_id=str(account["id"]),
        source=SOURCE,
        account_type=_map_type(account.get("type", ""), account.get("name", "")),
        label=account.get("name", ""),
        currency=currency_id,
        balance=balance,
        balance_eur=Decimal(str(account["balance_eur"])) if account.get("balance_eur") is not None else balance,
        price_eur=None,
        institution=account.get("company_name") or account.get("connection", {}).get("name"),
        iban=account.get("iban"),
        metadata=account,
    )


def normalize_wealth_account(account: dict, investments: list[dict]) -> NormalizedAccount:
    # Valorisation totale = somme des investissements
    total_valuation = sum(
        Decimal(str(inv.get("valuation", 0))) for inv in investments
    )
    if total_valuation == 0:
        total_valuation = Decimal(str(account.get("balance", 0)))

    currency = account.get("currency", {})
    currency_id = currency.get("id", "EUR") if isinstance(currency, dict) else str(currency)

    return NormalizedAccount(
        external_id=str(account["id"]),
        source=SOURCE,
        account_type=_map_type(account.get("type", ""), account.get("name", "")),
        label=account.get("name", ""),
        currency=currency_id,
        balance=total_valuation,
        balance_eur=total_valuation if currency_id == "EUR" else None,
        price_eur=None,
        institution=account.get("company_name") or account.get("connection", {}).get("name"),
        iban=None,
        metadata={**account, "investments": investments},
    )
