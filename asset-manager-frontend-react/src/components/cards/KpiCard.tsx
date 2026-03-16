import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/Card";

interface KpiCardProps {
  title: string;
  value: string;
  subtitle?: string;
  valueColor?: "positive" | "negative" | "warning" | "default";
  className?: string;
}

const valueColorClasses = {
  positive: "text-positive",
  negative: "text-negative",
  warning: "text-warning",
  default: "text-text-primary",
};

export function KpiCard({ title, value, subtitle, valueColor = "default", className }: KpiCardProps) {
  return (
    <Card className={cn("flex flex-col gap-1", className)}>
      <span className="text-xs font-semibold uppercase tracking-widest text-text-muted">
        {title}
      </span>
      <span
        className={cn(
          "text-2xl font-bold tabular-nums leading-tight mt-1",
          valueColorClasses[valueColor]
        )}
      >
        {value}
      </span>
      {subtitle && (
        <span className="text-xs text-text-muted">{subtitle}</span>
      )}
    </Card>
  );
}
