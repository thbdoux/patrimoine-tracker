import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useAccounts, useAccountHistory } from "@/hooks/useQuery";
import { Card, CardHeader } from "@/components/ui/Card";
import { PeriodSelector } from "@/components/ui/PeriodSelector";
import { Skeleton } from "@/components/ui/Skeleton";
import { KpiCard } from "@/components/cards/KpiCard";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  formatEur,
  formatDate,
  formatDateShort,
  formatPct,
  ACCOUNT_TYPE_LABELS,
  ACCOUNT_TYPE_COLORS,
} from "@/lib/utils";
import { chartTheme } from "@/lib/chartTheme";
import type { Period } from "@/lib/api";

export function AccountDetail() {
  const { id } = useParams<{ id: string }>();
  const [period, setPeriod] = useState<Period>("3M");

  const { data: accounts } = useAccounts();
  const { data: history } = useAccountHistory(id ?? "", period);

  const account = accounts?.find((a) => a.id === id);

  if (!account && accounts !== undefined) {
    return (
      <div className="text-center py-20 text-text-muted">Compte introuvable</div>
    );
  }

  const color = account
    ? (ACCOUNT_TYPE_COLORS[account.account_type] ?? "#94a3b8")
    : "#94a3b8";

  const chartData = history?.map((p) => ({
    ...p,
    label: formatDateShort(p.ts),
  }));

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Link
        to="/accounts"
        className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors duration-150"
      >
        <ArrowLeft size={14} />
        Comptes
      </Link>

      {/* Header */}
      <div className="flex items-center gap-3">
        <div
          className="w-3 h-3 rounded-full shrink-0"
          style={{ backgroundColor: color }}
        />
        <div>
          {account ? (
            <>
              <h1 className="text-2xl font-bold text-text-primary leading-tight">
                {account.label ?? account.institution ?? "—"}
              </h1>
              <p className="text-sm text-text-muted mt-0.5">
                {ACCOUNT_TYPE_LABELS[account.account_type] ?? account.account_type}
                {account.institution && ` · ${account.institution}`}
              </p>
            </>
          ) : (
            <Skeleton className="h-8 w-48" />
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCard
          title="Valeur EUR"
          value={account ? formatEur(account.balance_eur) : "—"}
        />
        {account?.balance != null && account.currency !== "EUR" && (
          <KpiCard
            title={`Solde ${account.currency ?? "natif"}`}
            value={account.balance.toLocaleString("fr-FR", { maximumFractionDigits: 6 })}
          />
        )}
        {account?.price_eur != null && (
          <KpiCard
            title="Prix unitaire"
            value={formatEur(account.price_eur, 2)}
          />
        )}
        {account?.change_1d_pct != null && (
          <KpiCard
            title="Variation 24h"
            value={formatPct(account.change_1d_pct)}
            valueColor={account.change_1d_pct >= 0 ? "positive" : "negative"}
            subtitle={account.change_1d != null ? formatEur(account.change_1d) : undefined}
          />
        )}
      </div>

      {/* History chart */}
      <Card>
        <CardHeader
          title="Historique"
          action={<PeriodSelector selected={period} onChange={setPeriod} />}
        />
        {chartData && chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={chartData} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="account-gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.25} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={chartTheme.gridColor} strokeDasharray="0" vertical={false} />
              <XAxis
                dataKey="label"
                tick={chartTheme.tickStyle}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
                minTickGap={60}
              />
              <YAxis
                tick={chartTheme.tickStyle}
                axisLine={false}
                tickLine={false}
                width={70}
                tickFormatter={(v) => formatEur(v)}
              />
              <Tooltip
                contentStyle={chartTheme.tooltipStyle}
                formatter={(value: number) => [formatEur(value), "Valeur EUR"]}
                labelFormatter={(label) => label}
              />
              <Area
                type="monotone"
                dataKey="balance_eur"
                stroke={color}
                strokeWidth={chartTheme.strokeWidth}
                fill="url(#account-gradient)"
                dot={false}
                activeDot={{ r: 4, fill: color, stroke: "#141720", strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <Skeleton className="h-60 w-full" />
        )}
      </Card>

      {/* Snapshots table */}
      {history && history.length > 0 && (
        <Card>
          <CardHeader title="Historique des snapshots" />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 pr-4 text-xs font-medium text-text-muted">Date</th>
                  <th className="text-right py-2 pr-4 text-xs font-medium text-text-muted">Solde natif</th>
                  <th className="text-right py-2 pr-4 text-xs font-medium text-text-muted">Valeur EUR</th>
                  {history.some((p) => p.price_eur != null) && (
                    <th className="text-right py-2 text-xs font-medium text-text-muted">Prix unitaire</th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {history.slice(0, 50).map((p) => (
                  <tr key={p.ts} className="hover:bg-elevated/50 transition-colors">
                    <td className="py-2.5 pr-4 text-text-muted text-xs">{formatDate(p.ts)}</td>
                    <td className="py-2.5 pr-4 text-right tabular-nums text-text-secondary">
                      {p.balance.toLocaleString("fr-FR", { maximumFractionDigits: 6 })}
                    </td>
                    <td className="py-2.5 pr-4 text-right tabular-nums text-text-primary font-medium">
                      {p.balance_eur != null ? formatEur(p.balance_eur) : "—"}
                    </td>
                    {history.some((h) => h.price_eur != null) && (
                      <td className="py-2.5 text-right tabular-nums text-text-secondary">
                        {p.price_eur != null ? formatEur(p.price_eur, 2) : "—"}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
