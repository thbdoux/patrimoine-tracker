import { useState } from "react";
import { usePerformance, useReturns, useStackedHistory, useAllocation } from "@/hooks/useQuery";
import { Card, CardHeader } from "@/components/ui/Card";
import { PeriodSelector } from "@/components/ui/PeriodSelector";
import { Skeleton } from "@/components/ui/Skeleton";
import { KpiCard } from "@/components/cards/KpiCard";
import { StackedAreaChart } from "@/components/charts/StackedAreaChart";
import { ReturnHistogram } from "@/components/charts/ReturnHistogram";
import { formatEur, formatPct, computeHHI, ACCOUNT_TYPE_LABELS, ACCOUNT_TYPE_COLORS } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { Period } from "@/lib/api";

export function Analytics() {
  const [period, setPeriod] = useState<Period>("1Y");

  const { data: perf } = usePerformance();
  const { data: returns } = useReturns(period);
  const { data: stacked } = useStackedHistory(period, "1D");
  const { data: allocation } = useAllocation();

  // Return stats
  const positiveDays = returns?.filter((r) => r.return_pct >= 0).length ?? 0;
  const negativeDays = returns?.filter((r) => r.return_pct < 0).length ?? 0;
  const bestDay = returns ? Math.max(...returns.map((r) => r.return_pct)) : null;
  const worstDay = returns ? Math.min(...returns.map((r) => r.return_pct)) : null;

  // HHI
  const hhi = allocation ? computeHHI(allocation.by_type.map((i) => ({ pct: i.pct }))) : null;
  const hhiScore = hhi != null ? Math.round(hhi * 100) : null; // scale to 0-10000
  const hhiLabel =
    hhiScore != null
      ? hhiScore < 1500
        ? "Bien diversifié"
        : hhiScore < 2500
        ? "Modérément concentré"
        : "Très concentré"
      : null;
  const hhiColor =
    hhiScore != null
      ? hhiScore < 1500
        ? "text-positive"
        : hhiScore < 2500
        ? "text-warning"
        : "text-negative"
      : "text-text-primary";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary">Analytiques</h1>

      {/* Performance KPIs */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-text-muted mb-3">
          Performance
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <KpiCard
            title="ATH"
            value={perf?.ath != null ? formatEur(perf.ath) : "—"}
            subtitle={perf?.ath_date ?? undefined}
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
        </div>
      </div>

      {/* Returns stats */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-text-muted mb-3">
          Statistiques de rendement
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <KpiCard
            title="Jours positifs"
            value={returns ? `${positiveDays}` : "—"}
            subtitle={returns ? `${((positiveDays / returns.length) * 100).toFixed(0)}% du total` : undefined}
            valueColor="positive"
          />
          <KpiCard
            title="Jours négatifs"
            value={returns ? `${negativeDays}` : "—"}
            subtitle={returns ? `${((negativeDays / returns.length) * 100).toFixed(0)}% du total` : undefined}
            valueColor="negative"
          />
          <KpiCard
            title="Meilleur jour"
            value={bestDay != null ? formatPct(bestDay) : "—"}
            valueColor="positive"
          />
          <KpiCard
            title="Pire jour"
            value={worstDay != null ? formatPct(worstDay) : "—"}
            valueColor="negative"
          />
        </div>
      </div>

      {/* HHI */}
      {allocation && hhiScore != null && (
        <Card>
          <CardHeader title="Indice de concentration (HHI)" />
          <div className="flex items-start gap-6 flex-wrap">
            <div>
              <div className={cn("text-4xl font-bold tabular-nums", hhiColor)}>
                {hhiScore.toLocaleString("fr-FR")}
              </div>
              <div className="text-xs text-text-muted mt-1">sur 10 000</div>
              <div className={cn("text-sm font-medium mt-2", hhiColor)}>{hhiLabel}</div>
            </div>
            <div className="flex-1 min-w-[200px]">
              <div className="bg-elevated rounded-full h-2 overflow-hidden mb-4">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(hhiScore / 100, 100)}%`,
                    background:
                      hhiScore < 1500
                        ? "#10b981"
                        : hhiScore < 2500
                        ? "#f59e0b"
                        : "#ef4444",
                  }}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                {allocation.by_type.map((item) => (
                  <div key={item.key} className="flex items-center gap-2 text-xs">
                    <div
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: ACCOUNT_TYPE_COLORS[item.key] ?? "#94a3b8" }}
                    />
                    <span className="text-text-secondary truncate">
                      {ACCOUNT_TYPE_LABELS[item.key] ?? item.key}
                    </span>
                    <span className="text-text-muted ml-auto tabular-nums">
                      {item.pct.toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Stacked chart */}
      <Card>
        <CardHeader
          title="Évolution par catégorie"
          action={<PeriodSelector selected={period} onChange={setPeriod} />}
        />
        {stacked && stacked.length > 0 ? (
          <StackedAreaChart data={stacked} />
        ) : (
          <Skeleton className="h-64 w-full" />
        )}
      </Card>

      {/* Return histogram */}
      <Card>
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div>
            <span className="text-xs font-semibold uppercase tracking-widest text-text-muted">
              Distribution des rendements journaliers
            </span>
            {returns && returns.length > 0 && (
              <div className="text-xs text-text-muted mt-0.5">
                Moyenne :{" "}
                <span className="text-text-secondary font-medium">
                  {formatPct(returns.reduce((s, r) => s + r.return_pct, 0) / returns.length)}
                </span>
                {" · "}
                {returns.length} jours
              </div>
            )}
          </div>
        </div>
        {returns && returns.length > 0 ? (
          <ReturnHistogram data={returns} />
        ) : (
          <Skeleton className="h-48 w-full" />
        )}
      </Card>
    </div>
  );
}
