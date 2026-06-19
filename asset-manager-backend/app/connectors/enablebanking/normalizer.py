from decimal import Decimal
from typing import Optional

from app.connectors.base import NormalizedAccount

SOURCE = "enablebanking"

# Mapping ISO 20022 ExternalCashAccountType (champ `cash_account_type`) → types normalisés.
# PSD2 expose surtout des comptes cash ; les comptes titres ne remontent pas de positions ici.
CASH_ACCOUNT_TYPE_MAP = {
    "CACC": "checking",   # Current
    "TRAN": "checking",   # Transacting
    "SVGS": "savings",    # Savings
    "LOAN": "loan",       # Loan
    "CARD": "checking",   # Card account
    "MGLD": "brokerage",  # Marginal lending
    "MOMA": "brokerage",  # Money market
    "ONDP": "checking",   # Overnight deposit
    "SLRY": "checking",   # Salary
}

# Ordre de préférence du type de solde à retenir (ISO 20022 BalanceType).
# On privilégie le disponible, puis le comptabilisé.
BALANCE_TYPE_PRIORITY = ("ITAV", "CLBD", "XPCD", "OPBD", "PRCD", "OTHR")


def _map_type(cash_account_type: Optional[str]) -> str:
    if not cash_account_type:
        return "other"
    return CASH_ACCOUNT_TYPE_MAP.get(cash_account_type.upper().strip(), "other")


def _extract_iban(account: dict) -> Optional[str]:
    account_id = account.get("account_id") or {}
    if isinstance(account_id, dict):
        return account_id.get("iban")
    return None


def _pick_balance(balances: list[dict]) -> tuple[Decimal, str]:
    """
    Sélectionne le solde le plus pertinent et sa devise.
    Suit BALANCE_TYPE_PRIORITY ; à défaut prend le premier disponible.
    """
    if not balances:
        return Decimal("0"), "EUR"

    by_type: dict[str, dict] = {}
    for b in balances:
        btype = (b.get("balance_type") or "").upper()
        by_type.setdefault(btype, b)

    chosen = next((by_type[t] for t in BALANCE_TYPE_PRIORITY if t in by_type), balances[0])
    amount_obj = chosen.get("balance_amount") or {}
    amount = Decimal(str(amount_obj.get("amount", "0")))
    currency = amount_obj.get("currency", "EUR")
    return amount, currency


def normalize_account(account: dict, balances: list[dict]) -> NormalizedAccount:
    balance, currency = _pick_balance(balances)

    # Libellé : on tente plusieurs champs renvoyés selon l'ASPSP
    label = (
        account.get("name")
        or account.get("product")
        or account.get("details")
        or _extract_iban(account)
        or "Compte"
    )

    institution = None
    aspsp = account.get("aspsp")
    if isinstance(aspsp, dict):
        institution = aspsp.get("name")

    return NormalizedAccount(
        external_id=str(account.get("uid") or account.get("identification_hash") or label),
        source=SOURCE,
        account_type=_map_type(account.get("cash_account_type")),
        label=str(label),
        currency=currency,
        balance=balance,
        # PSD2 fournit déjà les soldes dans la devise du compte ; EUR si déjà en EUR
        balance_eur=balance if currency == "EUR" else None,
        price_eur=None,
        institution=institution,
        iban=_extract_iban(account),
        metadata={**account, "balances": balances},
    )
