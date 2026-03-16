import { useState, useMemo } from "react";
import { useAccounts } from "@/hooks/useQuery";
import { Card, CardHeader } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { AccountRow } from "@/components/cards/AccountRow";
import { cn, formatEur, ACCOUNT_TYPE_LABELS, ACCOUNT_TYPE_COLORS, SOURCE_COLORS } from "@/lib/utils";

type FilterType = string | "all";

export function Accounts() {
  const { data: accounts, isLoading } = useAccounts();
  const [typeFilter, setTypeFilter] = useState<FilterType>("all");
  const [sourceFilter, setSourceFilter] = useState<FilterType>("all");

  const types = useMemo(() => {
    if (!accounts) return [];
    return [...new Set(accounts.map((a) => a.account_type))];
  }, [accounts]);

  const sources = useMemo(() => {
    if (!accounts) return [];
    return [...new Set(accounts.map((a) => a.source))];
  }, [accounts]);

  const filtered = useMemo(() => {
    if (!accounts) return [];
    return accounts
      .filter((a) => typeFilter === "all" || a.account_type === typeFilter)
      .filter((a) => sourceFilter === "all" || a.source === sourceFilter)
      .sort((a, b) => b.balance_eur - a.balance_eur);
  }, [accounts, typeFilter, sourceFilter]);

  const total = filtered.reduce((sum, a) => sum + a.balance_eur, 0);

  // Summary by type for filtered
  const byType = useMemo(() => {
    const map: Record<string, number> = {};
    filtered.forEach((a) => {
      map[a.account_type] = (map[a.account_type] ?? 0) + a.balance_eur;
    });
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  }, [filtered]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary mb-1">Comptes</h1>
        <p className="text-text-muted text-sm">
          Total filtré :{" "}
          <span className="text-text-primary font-semibold tabular-nums">
            {formatEur(total)}
          </span>
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        {/* Type filter */}
        <div>
          <p className="text-xs text-text-muted mb-2">Type</p>
          <div className="flex flex-wrap gap-1.5">
            <FilterPill
              label="Tous"
              active={typeFilter === "all"}
              onClick={() => setTypeFilter("all")}
            />
            {types.map((t) => (
              <FilterPill
                key={t}
                label={ACCOUNT_TYPE_LABELS[t] ?? t}
                active={typeFilter === t}
                color={ACCOUNT_TYPE_COLORS[t]}
                onClick={() => setTypeFilter(t)}
              />
            ))}
          </div>
        </div>

        {/* Source filter */}
        <div>
          <p className="text-xs text-text-muted mb-2">Source</p>
          <div className="flex flex-wrap gap-1.5">
            <FilterPill
              label="Toutes"
              active={sourceFilter === "all"}
              onClick={() => setSourceFilter("all")}
            />
            {sources.map((s) => (
              <FilterPill
                key={s}
                label={s}
                active={sourceFilter === s}
                color={SOURCE_COLORS[s]}
                onClick={() => setSourceFilter(s)}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Account list */}
        <div className="lg:col-span-2">
          <Card className="p-0">
            <div className="px-5 pt-5 pb-3">
              <CardHeader
                title={`${filtered.length} compte${filtered.length > 1 ? "s" : ""}`}
                className="mb-0"
              />
            </div>
            <div className="px-1 pb-2 divide-y divide-border">
              {isLoading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="px-4 py-3">
                    <Skeleton className="h-10 w-full" />
                  </div>
                ))
              ) : filtered.length === 0 ? (
                <div className="px-4 py-8 text-center text-text-muted text-sm">
                  Aucun compte
                </div>
              ) : (
                filtered.map((account) => (
                  <AccountRow key={account.id} account={account} />
                ))
              )}
            </div>
          </Card>
        </div>

        {/* Summary by type */}
        <div>
          <Card>
            <CardHeader title="Répartition" />
            <div className="space-y-3">
              {byType.map(([type, value]) => {
                const pct = total > 0 ? (value / total) * 100 : 0;
                return (
                  <div key={type}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <div className="flex items-center gap-1.5">
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: ACCOUNT_TYPE_COLORS[type] ?? "#94a3b8" }}
                        />
                        <span className="text-text-secondary">
                          {ACCOUNT_TYPE_LABELS[type] ?? type}
                        </span>
                      </div>
                      <span className="text-text-primary tabular-nums font-medium">
                        {formatEur(value)}
                      </span>
                    </div>
                    <div className="bg-elevated rounded-full h-1 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: ACCOUNT_TYPE_COLORS[type] ?? "#94a3b8",
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

interface FilterPillProps {
  label: string;
  active: boolean;
  color?: string;
  onClick: () => void;
}

function FilterPill({ label, active, color, onClick }: FilterPillProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-pill px-3 py-1.5 text-xs font-medium border transition-all duration-150",
        active
          ? "bg-accent/15 text-accent border-accent/30"
          : "bg-elevated text-text-secondary border-border hover:text-text-primary"
      )}
    >
      {color && (
        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
      )}
      {label}
    </button>
  );
}
