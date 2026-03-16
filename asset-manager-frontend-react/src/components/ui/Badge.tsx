import { cn } from "@/lib/utils";

type BadgeVariant = "positive" | "negative" | "neutral" | "accent";

interface BadgeProps {
  variant?: BadgeVariant;
  className?: string;
  children: React.ReactNode;
}

const variantClasses: Record<BadgeVariant, string> = {
  positive: "bg-positive/10 text-positive border border-positive/20",
  negative: "bg-negative/10 text-negative border border-negative/20",
  neutral: "bg-elevated text-text-secondary border border-border",
  accent: "bg-accent/10 text-accent border border-accent/20",
};

export function Badge({ variant = "neutral", className, children }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-pill px-2.5 py-0.5 text-xs font-medium",
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
