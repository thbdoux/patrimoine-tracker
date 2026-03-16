#!/usr/bin/env bash
set -euo pipefail

DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_NAME="${PGDATABASE:-patrimoine_db}"
DB_USER="${PGUSER:-patrimoine}"
DB_PASS="${PGPASSWORD:-password}"

psql() {
  PGPASSWORD="$DB_PASS" command psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$@"
}

echo "=========================================="
echo " COMPTES PAR SOURCE"
echo "=========================================="
psql -c "
SELECT
  source,
  account_type,
  COUNT(*) AS nb_comptes,
  COUNT(*) FILTER (WHERE is_active) AS actifs
FROM accounts
GROUP BY source, account_type
ORDER BY source, account_type;
"

echo "=========================================="
echo " DERNIER SNAPSHOT PAR COMPTE"
echo "=========================================="
psql -c "
SELECT
  a.source,
  a.label,
  a.account_type,
  a.currency,
  a.institution,
  s.balance,
  s.balance_eur,
  s.captured_at
FROM accounts a
JOIN LATERAL (
  SELECT balance, balance_eur, captured_at
  FROM account_snapshots
  WHERE account_id = a.id
  ORDER BY captured_at DESC
  LIMIT 1
) s ON true
WHERE a.is_active
ORDER BY a.source, s.balance_eur DESC NULLS LAST;
"

echo "=========================================="
echo " TOTAL PAR SOURCE (EUR)"
echo "=========================================="
psql -c "
SELECT
  a.source,
  ROUND(SUM(s.balance_eur)::numeric, 2) AS total_eur,
  COUNT(*) AS nb_comptes
FROM accounts a
JOIN LATERAL (
  SELECT balance_eur
  FROM account_snapshots
  WHERE account_id = a.id
  ORDER BY captured_at DESC
  LIMIT 1
) s ON true
WHERE a.is_active
GROUP BY a.source
ORDER BY total_eur DESC NULLS LAST;
"

echo "=========================================="
echo " TOTAL PATRIMOINE (EUR)"
echo "=========================================="
psql -c "
SELECT ROUND(SUM(s.balance_eur)::numeric, 2) AS total_eur
FROM accounts a
JOIN LATERAL (
  SELECT balance_eur
  FROM account_snapshots
  WHERE account_id = a.id
  ORDER BY captured_at DESC
  LIMIT 1
) s ON true
WHERE a.is_active;
"
