import { Link } from "react-router-dom";
import { cn, formatEur, formatPct, ACCOUNT_TYPE_LABELS, ACCOUNT_TYPE_COLORS } from "@/lib/utils";
import type { Account } from "@/lib/api";

interface AccountRowProps {
  account: Account;
  showLink?: boolean;
}

export function AccountRow({ account, showLink = true }: AccountRowProps) {
  const color = ACCOUNT_TYPE_COLORS[account.account_type] ?? "#94a3b8";
  const label = account.label ?? account.institution ?? "—";
  const typeLabel = ACCOUNT_TYPE_LABELS[account.account_type] ?? account.account_type;
  const positive = (account.change_1d_pct ?? 0) >= 0;

  const content = (
    <div className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-elevated transition-colors duration-150 group">
      {/* Color dot */}
      <div
        className="w-2 h-2 rounded-full shrink-0"
        style={{ backgroundColor: color }}
      />

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-text-primary truncate">{label}</div>
        <div className="text-xs text-text-muted">
          {typeLabel}
          {account.institution && ` · ${account.institution}`}
        </div>
      </div>

      {/* Balance + change */}
      <div className="text-right shrink-0">
        <div className="text-sm font-semibold tabular-nums text-text-primary">
          {formatEur(account.balance_eur)}
        </div>
        {account.change_1d_pct !== null && (
          <div
            className={cn(
              "text-xs tabular-nums font-medium",
              positive ? "text-positive" : "text-negative"
            )}
          >
            {formatPct(account.change_1d_pct)}
          </div>
        )}
      </div>
    </div>
  );

  if (showLink) {
    return (
      <Link to={`/accounts/${account.id}`} className="block">
        {content}
      </Link>
    );
  }

  return content;
}
