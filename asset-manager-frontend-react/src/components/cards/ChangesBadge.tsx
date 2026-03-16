import { cn, formatEur, formatPct } from "@/lib/utils";
import type { Change } from "@/lib/api";

interface ChangesBadgeProps {
  label: string;
  change: Change;
  compact?: boolean;
  className?: string;
}

export function ChangesBadge({ label, change, compact = false, className }: ChangesBadgeProps) {
  const positive = change.pct >= 0;

  return (
    <div
      className={cn(
        "flex flex-col items-center rounded-pill px-3 py-2 border transition-colors duration-150",
        positive
          ? "bg-positive/10 border-positive/20"
          : "bg-negative/10 border-negative/20",
        className
      )}
    >
      <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider">
        {label}
      </span>
      <span
        className={cn(
          "text-sm font-bold tabular-nums",
          positive ? "text-positive" : "text-negative"
        )}
      >
        {formatPct(change.pct)}
      </span>
      {!compact && (
        <span
          className={cn(
            "text-[10px] tabular-nums",
            positive ? "text-positive/70" : "text-negative/70"
          )}
        >
          {positive ? "+" : ""}
          {formatEur(change.value)}
        </span>
      )}
    </div>
  );
}
