import { useState } from "react";
import {
  useOverview,
  useAllocation,
  useHistory,
  useAccounts,
  usePerformance,
} from "@/hooks/useQuery";
import { Card, CardHeader } from "@/components/ui/Card";
import { PeriodSelector } from "@/components/ui/PeriodSelector";
import { Skeleton } from "@/components/ui/Skeleton";
import { KpiCard } from "@/components/cards/KpiCard";
import { ChangesBadge } from "@/components/cards/ChangesBadge";
import { AccountRow } from "@/components/cards/AccountRow";
import { SyncStatusDot } from "@/components/cards/SyncStatusDot";
import { PatrimoineChart } from "@/components/charts/PatrimoineChart";
import { AllocationDonut } from "@/components/charts/AllocationDonut";
import {
  formatEur,
  formatDate,
  formatPct,
  ACCOUNT_TYPE_LABELS,
  ACCOUNT_TYPE_COLORS,
  SOURCE_COLORS,
} from "@/lib/utils";
import type { Period } from "@/lib/api";

export function Dashboard() {
  const [period, setPeriod] = useState<Period>("1Y");

  const { data: overview } = useOverview();
  const { data: allocation } = useAllocation();
  const { data: history } = useHistory(period, "1D");
  const { data: accounts } = useAccounts();
  const { data: perf } = usePerformance();

  const sortedAccounts = accounts
    ? [...accounts].sort((a, b) => b.balance_eur - a.balance_eur).slice(0, 10)
    : [];

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div>
        <div className="flex items-start justify-between flex-wrap gap-4 mb-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-text-muted mb-1">
              Patrimoine total
            </p>
            {overview ? (
              <h1 className="text-5xl font-bold tabular-nums text-text-primary leading-none">
                {formatEur(overview.total_eur)}
              </h1>
            ) : (
              <Skeleton className="h-12 w-64 mt-1" />
            )}
            {overview?.last_updated && (
              <p className="text-xs text-text-muted mt-2">
                Mis à jour le {formatDate(overview.last_updated)}
              </p>
            )}
          </div>
          <SyncStatusDot />
        </div>

        {/* Changes badges */}
        {overview ? (
          <div className="flex flex-wrap gap-2">
            <ChangesBadge label="24h" change={overview.changes["1d"]} />
            <ChangesBadge label="7j" change={overview.changes["7d"]} />
            <ChangesBadge label="30j" change={overview.changes["30d"]} />
            <ChangesBadge label="1an" change={overview.changes["1y"]} />
            <ChangesBadge label="Début" change={overview.changes.inception} />
          </div>
        ) : (
          <div className="flex gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-20 rounded-pill" />
            ))}
          </div>
        )}
      </div>

      {/* Chart */}
      <Card>
        <CardHeader
          title="Évolution"
          action={
            <PeriodSelector selected={period} onChange={setPeriod} />
          }
        />
        {history && history.length > 0 ? (
          <PatrimoineChart data={history} />
        ) : (
          <Skeleton className="h-64 w-full" />
        )}
      </Card>

      {/* KPI Cards */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-text-muted mb-3">
          Performance
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <KpiCard
            title="ATH"
            value={perf?.ath != null ? formatEur(perf.ath) : "—"}
            subtitle={perf?.ath_date ?? undefined}
          />
          <KpiCard
            title="Drawdown actuel"
            value={perf?.current_drawdown_pct != null ? formatPct(perf.current_drawdown_pct) : "—"}
            valueColor={
              perf?.current_drawdown_pct != null && perf.current_drawdown_pct < 0
                ? "negative"
                : "default"
            }
          />
          <KpiCard
            title="Max Drawdown"
            value={perf?.max_drawdown_pct != null ? formatPct(perf.max_drawdown_pct) : "—"}
            valueColor={
              perf?.max_drawdown_pct != null && perf.max_drawdown_pct < 0
                ? "negative"
                : "default"
            }
          />
          <KpiCard
            title="Volatilité 30j"
            value={
              perf?.volatility_30d_annualised != null
                ? `${perf.volatility_30d_annualised.toFixed(1)}%`
                : "—"
            }
            subtitle="annualisée"
          />
          <KpiCard
            title="Volatilité 1an"
            value={
              perf?.volatility_1y_annualised != null
                ? `${perf.volatility_1y_annualised.toFixed(1)}%`
                : "—"
            }
            subtitle="annualisée"
          />
          <KpiCard
            title="Perf. totale"
            value={
              overview?.changes.inception
                ? formatPct(overview.changes.inception.pct)
                : "—"
            }
            valueColor={
              overview?.changes.inception
                ? overview.changes.inception.pct >= 0
                  ? "positive"
                  : "negative"
                : "default"
            }
          />
        </div>
      </div>

      {/* Allocation + Top accounts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* By type */}
        <Card>
          <CardHeader title="Par catégorie" />
          {allocation ? (
            <AllocationDonut
              data={allocation.by_type}
              colors={ACCOUNT_TYPE_COLORS}
              labelMap={ACCOUNT_TYPE_LABELS}
            />
          ) : (
            <Skeleton className="h-52 w-full" />
          )}
        </Card>

        {/* By source */}
        <Card>
          <CardHeader title="Par source" />
          {allocation ? (
            <AllocationDonut
              data={allocation.by_source}
              colors={SOURCE_COLORS}
            />
          ) : (
            <Skeleton className="h-52 w-full" />
          )}
        </Card>

        {/* Top accounts */}
        <Card className="p-0">
          <div className="px-5 pt-5 pb-3">
            <CardHeader title="Top comptes" className="mb-0" />
          </div>
          <div className="px-1 pb-2">
            {sortedAccounts.length > 0 ? (
              sortedAccounts.map((account) => (
                <AccountRow key={account.id} account={account} />
              ))
            ) : (
              <div className="px-4 py-8">
                {accounts === undefined ? (
                  <Skeleton className="h-full w-full min-h-[200px]" />
                ) : (
                  <p className="text-text-muted text-sm text-center">Aucun compte</p>
                )}
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Allocation detail table */}
      {allocation && allocation.detail.length > 0 && (
        <Card>
          <CardHeader title="Détail allocation" />
          <div className="space-y-2">
            {allocation.by_type.map((item) => (
              <div key={item.key} className="flex items-center gap-3">
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: ACCOUNT_TYPE_COLORS[item.key] ?? "#94a3b8" }}
                />
                <span className="text-sm text-text-secondary flex-1">
                  {ACCOUNT_TYPE_LABELS[item.key] ?? item.key}
                </span>
                <div className="flex-1 max-w-xs bg-elevated rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${item.pct}%`,
                      backgroundColor: ACCOUNT_TYPE_COLORS[item.key] ?? "#94a3b8",
                    }}
                  />
                </div>
                <span className="text-sm font-medium tabular-nums text-text-primary w-24 text-right">
                  {formatEur(item.value_eur)}
                </span>
                <span className="text-xs text-text-muted tabular-nums w-10 text-right">
                  {item.pct.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
