from decimal import Decimal
from typing import Optional

from app.connectors.base import NormalizedAccount

DUST_THRESHOLD = Decimal("0.00000001")
SOURCE = "binance"


def normalize_spot(
    asset: str,
    free: Decimal,
    locked: Decimal,
    price_usdt: Optional[Decimal],
    eurusdt_rate: Optional[Decimal],
    raw: dict,
) -> NormalizedAccount:
    balance = free + locked
    balance_eur: Optional[Decimal] = None
    price_eur: Optional[Decimal] = None

    if price_usdt is not None and eurusdt_rate is not None and eurusdt_rate > 0:
        price_eur = price_usdt / eurusdt_rate
        balance_eur = balance * price_eur
    elif asset == "USDT" and eurusdt_rate is not None and eurusdt_rate > 0:
        price_eur = Decimal("1") / eurusdt_rate
        balance_eur = balance * price_eur
    elif asset == "EUR":
        price_eur = Decimal("1")
        balance_eur = balance

    return NormalizedAccount(
        external_id=f"spot_{asset}",
        source=SOURCE,
        account_type="crypto_spot",
        label=f"{asset} Spot",
        currency=asset,
        balance=balance,
        balance_eur=balance_eur,
        price_eur=price_eur,
        institution="Binance",
        iban=None,
        metadata=raw,
    )


def normalize_earn(
    asset: str,
    amount: Decimal,
    price_usdt: Optional[Decimal],
    eurusdt_rate: Optional[Decimal],
    raw: dict,
) -> NormalizedAccount:
    balance_eur: Optional[Decimal] = None
    price_eur: Optional[Decimal] = None

    if price_usdt is not None and eurusdt_rate is not None and eurusdt_rate > 0:
        price_eur = price_usdt / eurusdt_rate
        balance_eur = amount * price_eur

    return NormalizedAccount(
        external_id=f"earn_{asset}",
        source=SOURCE,
        account_type="crypto_staking",
        label=f"{asset} Earn",
        currency=asset,
        balance=amount,
        balance_eur=balance_eur,
        price_eur=price_eur,
        institution="Binance",
        iban=None,
        metadata=raw,
    )


def is_dust(balance: Decimal) -> bool:
    return balance < DUST_THRESHOLD
