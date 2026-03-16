import { cn } from "@/lib/utils";
import type { Period } from "@/lib/api";

const PERIOD_LABELS: Record<Period, string> = {
  "7D": "7j",
  "1M": "1m",
  "3M": "3m",
  "6M": "6m",
  "1Y": "1an",
  ALL: "Tout",
};

interface PeriodSelectorProps {
  periods?: Period[];
  selected: Period;
  onChange: (period: Period) => void;
  className?: string;
}

export function PeriodSelector({
  periods = ["7D", "1M", "3M", "6M", "1Y", "ALL"],
  selected,
  onChange,
  className,
}: PeriodSelectorProps) {
  return (
    <div className={cn("flex gap-1", className)}>
      {periods.map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={cn(
            "rounded-pill px-3 py-1 text-xs font-medium transition-all duration-150",
            selected === p
              ? "bg-accent text-white"
              : "text-text-secondary hover:bg-elevated hover:text-text-primary"
          )}
        >
          {PERIOD_LABELS[p]}
        </button>
      ))}
    </div>
  );
}
