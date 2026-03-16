"""
Analytics service: aggregation, KPI computation, and time-series queries.
All monetary values are in EUR unless noted otherwise.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _period_to_days(period: str) -> int:
    mapping = {"7D": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "ALL": 365 * 10}
    return mapping.get(period.upper(), 365)


def _granularity_to_interval(granularity: str) -> str:
    mapping = {"1H": "1 hour", "6H": "6 hours", "1D": "1 day", "1W": "7 days", "1M": "30 days"}
    return mapping.get(granularity.upper(), "1 day")


# ---------------------------------------------------------------------------
# Latest total patrimoine as-of a given timestamp
# ---------------------------------------------------------------------------

async def get_total_at(db: AsyncSession, at: datetime | None = None) -> Decimal:
    """
    Sum of the most recent balance_eur for each active account, as of `at`.
    Uses DISTINCT ON to pick the latest snapshot per account.
    """
    if at is None:
        at = _now()
    result = await db.execute(
        text("""
            WITH latest AS (
                SELECT DISTINCT ON (s.account_id)
                    s.balance_eur
                FROM account_snapshots s
                JOIN accounts a ON a.id = s.account_id
                WHERE a.is_active = true
                  AND s.balance_eur IS NOT NULL
                  AND s.captured_at <= :at
                ORDER BY s.account_id, s.captured_at DESC
            )
            SELECT COALESCE(SUM(balance_eur), 0) AS total_eur
            FROM latest
        """),
        {"at": at},
    )
    row = result.one()
    return Decimal(row.total_eur or 0)


# ---------------------------------------------------------------------------
# Overview: total + variations
# ---------------------------------------------------------------------------

async def get_overview(db: AsyncSession) -> dict[str, Any]:
    now = _now()
    current = await get_total_at(db, now)

    reference_offsets = {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365),
    }

    changes: dict[str, dict[str, Any]] = {}
    for label, delta in reference_offsets.items():
        ref = await get_total_at(db, now - delta)
        if ref and ref > 0:
            diff = current - ref
            pct = float(diff / ref * 100)
        else:
            diff = Decimal(0)
            pct = 0.0
        changes[label] = {"value": float(diff), "pct": round(pct, 2)}

    # Inception = first ever snapshot
    result = await db.execute(text("SELECT MIN(captured_at) FROM account_snapshots"))
    inception_at = result.scalar()
    if inception_at:
        inception_val = await get_total_at(db, inception_at + timedelta(minutes=10))
        diff_inception = current - inception_val
        pct_inception = float(diff_inception / inception_val * 100) if inception_val > 0 else 0.0
        changes["inception"] = {"value": float(diff_inception), "pct": round(pct_inception, 2)}
    else:
        changes["inception"] = {"value": 0.0, "pct": 0.0}

    # Last updated = latest snapshot timestamp across all accounts
    result2 = await db.execute(text("SELECT MAX(captured_at) FROM account_snapshots"))
    last_updated = result2.scalar()

    return {
        "total_eur": float(current),
        "changes": changes,
        "last_updated": last_updated.isoformat() if last_updated else None,
    }


# ---------------------------------------------------------------------------
# Patrimoine history (time series)
# ---------------------------------------------------------------------------

async def get_patrimoine_history(
    db: AsyncSession,
    period: str = "1Y",
    granularity: str = "1D",
) -> list[dict[str, Any]]:
    """
    Time series of total patrimoine with forward-fill per account.
    For each point in the generated series, we take the last known balance
    for every active account (LATERAL subquery).
    """
    days = _period_to_days(period)
    interval = _granularity_to_interval(granularity)

    result = await db.execute(
        text(f"""
            WITH dates AS (
                SELECT generate_series(
                    NOW() - INTERVAL '{days} days',
                    NOW(),
                    INTERVAL '{interval}'
                ) AS ts
            ),
            active_accounts AS (
                SELECT id FROM accounts WHERE is_active = true
            )
            SELECT
                d.ts,
                COALESCE(SUM(s.balance_eur), 0) AS total_eur
            FROM dates d
            CROSS JOIN active_accounts aa
            LEFT JOIN LATERAL (
                SELECT balance_eur
                FROM account_snapshots
                WHERE account_id = aa.id
                  AND balance_eur IS NOT NULL
                  AND captured_at <= d.ts
                ORDER BY captured_at DESC
                LIMIT 1
            ) s ON true
            GROUP BY d.ts
            HAVING COALESCE(SUM(s.balance_eur), 0) > 0
            ORDER BY d.ts
        """)
    )
    rows = result.fetchall()
    return [{"ts": row.ts.isoformat(), "total_eur": float(row.total_eur)} for row in rows]


# ---------------------------------------------------------------------------
# Allocation breakdown
# ---------------------------------------------------------------------------

async def get_allocation(db: AsyncSession) -> dict[str, Any]:
    """
    Current allocation breakdown by account_type and by source.
    """
    result = await db.execute(
        text("""
            WITH latest AS (
                SELECT DISTINCT ON (s.account_id)
                    s.account_id, s.balance_eur
                FROM account_snapshots s
                JOIN accounts a ON a.id = s.account_id
                WHERE a.is_active = true
                  AND s.balance_eur IS NOT NULL
                ORDER BY s.account_id, s.captured_at DESC
            )
            SELECT
                a.account_type,
                a.source,
                SUM(l.balance_eur) AS value_eur
            FROM latest l
            JOIN accounts a ON a.id = l.account_id
            GROUP BY a.account_type, a.source
            ORDER BY value_eur DESC
        """)
    )
    rows = result.fetchall()

    total = sum(float(r.value_eur or 0) for r in rows)

    by_type: dict[str, float] = {}
    by_source: dict[str, float] = {}
    items = []

    for row in rows:
        v = float(row.value_eur or 0)
        pct = round(v / total * 100, 2) if total > 0 else 0.0
        items.append({
            "account_type": row.account_type,
            "source": row.source,
            "value_eur": round(v, 2),
            "pct": pct,
        })
        by_type[row.account_type] = by_type.get(row.account_type, 0.0) + v
        by_source[row.source] = by_source.get(row.source, 0.0) + v

    return {
        "total_eur": round(total, 2),
        "by_type": [
            {"key": k, "value_eur": round(v, 2), "pct": round(v / total * 100, 2) if total > 0 else 0.0}
            for k, v in sorted(by_type.items(), key=lambda x: -x[1])
        ],
        "by_source": [
            {"key": k, "value_eur": round(v, 2), "pct": round(v / total * 100, 2) if total > 0 else 0.0}
            for k, v in sorted(by_source.items(), key=lambda x: -x[1])
        ],
        "detail": items,
    }


# ---------------------------------------------------------------------------
# Stacked history by account_type (for stacked area chart)
# ---------------------------------------------------------------------------

async def get_stacked_history(
    db: AsyncSession,
    period: str = "1Y",
    granularity: str = "1D",
) -> list[dict[str, Any]]:
    """
    Time series with one column per account_type (forward-filled).
    """
    days = _period_to_days(period)
    interval = _granularity_to_interval(granularity)

    result = await db.execute(
        text(f"""
            WITH dates AS (
                SELECT generate_series(
                    NOW() - INTERVAL '{days} days',
                    NOW(),
                    INTERVAL '{interval}'
                ) AS ts
            ),
            active_accounts AS (
                SELECT id, account_type FROM accounts WHERE is_active = true
            )
            SELECT
                d.ts,
                aa.account_type,
                COALESCE(SUM(s.balance_eur), 0) AS value_eur
            FROM dates d
            CROSS JOIN active_accounts aa
            LEFT JOIN LATERAL (
                SELECT balance_eur
                FROM account_snapshots
                WHERE account_id = aa.id
                  AND balance_eur IS NOT NULL
                  AND captured_at <= d.ts
                ORDER BY captured_at DESC
                LIMIT 1
            ) s ON true
            GROUP BY d.ts, aa.account_type
            ORDER BY d.ts, aa.account_type
        """)
    )
    rows = result.fetchall()

    # Pivot: group by ts, collect {account_type: value} per point
    from collections import defaultdict
    points: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        ts = row.ts.isoformat()
        points[ts][row.account_type] = float(row.value_eur or 0)

    # Filter out zero-total points
    result_list = []
    for ts in sorted(points.keys()):
        data = points[ts]
        if sum(data.values()) > 0:
            result_list.append({"ts": ts, **data})
    return result_list


# ---------------------------------------------------------------------------
# Accounts list with latest snapshot
# ---------------------------------------------------------------------------

async def get_accounts_with_latest(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        text("""
            WITH latest AS (
                SELECT DISTINCT ON (s.account_id)
                    s.account_id,
                    s.balance,
                    s.balance_eur,
                    s.price_eur,
                    s.captured_at
                FROM account_snapshots s
                JOIN accounts a ON a.id = s.account_id
                WHERE a.is_active = true
                ORDER BY s.account_id, s.captured_at DESC
            ),
            prev_day AS (
                SELECT DISTINCT ON (s.account_id)
                    s.account_id,
                    s.balance_eur AS prev_balance_eur
                FROM account_snapshots s
                JOIN accounts a ON a.id = s.account_id
                WHERE a.is_active = true
                  AND s.balance_eur IS NOT NULL
                  AND s.captured_at <= NOW() - INTERVAL '24 hours'
                ORDER BY s.account_id, s.captured_at DESC
            )
            SELECT
                a.id,
                a.external_id,
                a.source,
                a.account_type,
                a.label,
                a.currency,
                a.institution,
                l.balance,
                l.balance_eur,
                l.price_eur,
                l.captured_at,
                pd.prev_balance_eur
            FROM accounts a
            LEFT JOIN latest l ON l.account_id = a.id
            LEFT JOIN prev_day pd ON pd.account_id = a.id
            WHERE a.is_active = true
            ORDER BY l.balance_eur DESC NULLS LAST
        """)
    )
    rows = result.fetchall()
    accounts = []
    for row in rows:
        balance_eur = float(row.balance_eur or 0)
        prev = float(row.prev_balance_eur or 0) if row.prev_balance_eur else None
        change_1d = None
        change_1d_pct = None
        if prev and prev > 0:
            change_1d = round(balance_eur - prev, 2)
            change_1d_pct = round((balance_eur - prev) / prev * 100, 2)
        accounts.append({
            "id": str(row.id),
            "source": row.source,
            "account_type": row.account_type,
            "label": row.label,
            "currency": row.currency,
            "institution": row.institution,
            "balance": float(row.balance) if row.balance is not None else None,
            "balance_eur": round(balance_eur, 2),
            "price_eur": float(row.price_eur) if row.price_eur is not None else None,
            "captured_at": row.captured_at.isoformat() if row.captured_at else None,
            "change_1d": change_1d,
            "change_1d_pct": change_1d_pct,
        })
    return accounts


# ---------------------------------------------------------------------------
# Account history
# ---------------------------------------------------------------------------

async def get_account_history(
    db: AsyncSession,
    account_id: str,
    period: str = "3M",
) -> list[dict[str, Any]]:
    days = _period_to_days(period)
    result = await db.execute(
        text(f"""
            SELECT captured_at, balance, balance_eur, price_eur
            FROM account_snapshots
            WHERE account_id = :account_id
              AND captured_at >= NOW() - INTERVAL '{days} days'
            ORDER BY captured_at
        """),
        {"account_id": account_id},
    )
    rows = result.fetchall()
    return [
        {
            "ts": row.captured_at.isoformat(),
            "balance": float(row.balance),
            "balance_eur": float(row.balance_eur) if row.balance_eur is not None else None,
            "price_eur": float(row.price_eur) if row.price_eur is not None else None,
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Performance metrics (ATH, drawdown, volatility, TWR)
# ---------------------------------------------------------------------------

async def get_performance_metrics(db: AsyncSession) -> dict[str, Any]:
    """
    Compute ATH, max drawdown, annualised volatility, and approximate TWR
    from the daily patrimoine history (last 2 years).
    """
    # Fetch daily totals for all-time (or up to 2 years for perf)
    result = await db.execute(
        text("""
            WITH dates AS (
                SELECT generate_series(
                    NOW() - INTERVAL '730 days',
                    NOW(),
                    INTERVAL '1 day'
                ) AS ts
            ),
            active_accounts AS (
                SELECT id FROM accounts WHERE is_active = true
            )
            SELECT
                d.ts::date AS day,
                COALESCE(SUM(s.balance_eur), 0) AS total_eur
            FROM dates d
            CROSS JOIN active_accounts aa
            LEFT JOIN LATERAL (
                SELECT balance_eur
                FROM account_snapshots
                WHERE account_id = aa.id
                  AND balance_eur IS NOT NULL
                  AND captured_at <= d.ts
                ORDER BY captured_at DESC
                LIMIT 1
            ) s ON true
            GROUP BY d.ts::date
            HAVING COALESCE(SUM(s.balance_eur), 0) > 0
            ORDER BY day
        """)
    )
    rows = result.fetchall()

    if not rows:
        return {
            "ath": None,
            "ath_date": None,
            "max_drawdown_pct": None,
            "current_drawdown_pct": None,
            "volatility_30d_annualised": None,
            "volatility_1y_annualised": None,
        }

    values = [float(r.total_eur) for r in rows]
    dates = [r.day for r in rows]

    # ATH
    ath_idx = values.index(max(values))
    ath = values[ath_idx]
    ath_date = dates[ath_idx]

    # Max drawdown: min of (value - running_max) / running_max
    running_max = values[0]
    max_dd = 0.0
    current_dd = 0.0
    for v in values:
        running_max = max(running_max, v)
        dd = (v - running_max) / running_max * 100 if running_max > 0 else 0.0
        max_dd = min(max_dd, dd)
    current = values[-1]
    current_dd = (current - ath) / ath * 100 if ath > 0 else 0.0

    # Daily returns
    returns = []
    for i in range(1, len(values)):
        if values[i - 1] > 0:
            returns.append((values[i] - values[i - 1]) / values[i - 1])

    def std(lst: list[float]) -> float:
        if len(lst) < 2:
            return 0.0
        mean = sum(lst) / len(lst)
        variance = sum((x - mean) ** 2 for x in lst) / (len(lst) - 1)
        return math.sqrt(variance)

    vol_30d = std(returns[-30:]) * math.sqrt(252) * 100 if len(returns) >= 2 else None
    vol_1y = std(returns[-365:]) * math.sqrt(252) * 100 if len(returns) >= 30 else None

    return {
        "ath": round(ath, 2),
        "ath_date": ath_date.isoformat() if ath_date else None,
        "max_drawdown_pct": round(max_dd, 2),
        "current_drawdown_pct": round(current_dd, 2),
        "volatility_30d_annualised": round(vol_30d, 2) if vol_30d is not None else None,
        "volatility_1y_annualised": round(vol_1y, 2) if vol_1y is not None else None,
    }


# ---------------------------------------------------------------------------
# Return distribution (for histogram)
# ---------------------------------------------------------------------------

async def get_return_distribution(db: AsyncSession, period: str = "1Y") -> list[dict[str, Any]]:
    """Daily returns as list of {date, return_pct} for the last `period`."""
    days = _period_to_days(period)
    result = await db.execute(
        text(f"""
            WITH dates AS (
                SELECT generate_series(
                    NOW() - INTERVAL '{days} days',
                    NOW(),
                    INTERVAL '1 day'
                ) AS ts
            ),
            active_accounts AS (SELECT id FROM accounts WHERE is_active = true),
            daily_totals AS (
                SELECT
                    d.ts::date AS day,
                    COALESCE(SUM(s.balance_eur), 0) AS total_eur
                FROM dates d
                CROSS JOIN active_accounts aa
                LEFT JOIN LATERAL (
                    SELECT balance_eur
                    FROM account_snapshots
                    WHERE account_id = aa.id
                      AND balance_eur IS NOT NULL
                      AND captured_at <= d.ts
                    ORDER BY captured_at DESC
                    LIMIT 1
                ) s ON true
                GROUP BY d.ts::date
                HAVING COALESCE(SUM(s.balance_eur), 0) > 0
                ORDER BY day
            )
            SELECT
                day,
                total_eur,
                LAG(total_eur) OVER (ORDER BY day) AS prev_total_eur
            FROM daily_totals
        """)
    )
    rows = result.fetchall()
    result_list = []
    for row in rows:
        if row.prev_total_eur and float(row.prev_total_eur) > 0:
            ret = (float(row.total_eur) - float(row.prev_total_eur)) / float(row.prev_total_eur) * 100
            result_list.append({"date": row.day.isoformat(), "return_pct": round(ret, 4)})
    return result_list


# ---------------------------------------------------------------------------
# Sync status
# ---------------------------------------------------------------------------

async def get_sync_status(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        text("""
            SELECT DISTINCT ON (source)
                source, status, started_at, finished_at, accounts_synced, error_message
            FROM sync_logs
            ORDER BY source, started_at DESC
        """)
    )
    rows = result.fetchall()
    return [
        {
            "source": row.source,
            "status": row.status,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            "accounts_synced": row.accounts_synced,
            "error_message": row.error_message,
        }
        for row in rows
    ]
