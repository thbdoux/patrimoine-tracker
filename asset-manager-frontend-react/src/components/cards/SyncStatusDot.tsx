import { cn, formatDate } from "@/lib/utils";
import { useSyncStatus } from "@/hooks/useQuery";

const STATUS_COLORS: Record<string, string> = {
  success: "bg-positive",
  partial: "bg-warning",
  failed: "bg-negative",
  running: "bg-accent animate-pulse",
};

export function SyncStatusDot() {
  const { data } = useSyncStatus();

  if (!data || data.length === 0) return null;

  return (
    <div className="flex items-center gap-3">
      {data.map((s) => (
        <div key={s.source} className="flex items-center gap-1.5" title={
          s.finished_at ? `${s.source}: ${formatDate(s.finished_at)}` : s.source
        }>
          <div
            className={cn(
              "w-1.5 h-1.5 rounded-full",
              STATUS_COLORS[s.status] ?? "bg-text-muted"
            )}
          />
          <span className="text-xs text-text-muted capitalize">{s.source}</span>
        </div>
      ))}
    </div>
  );
}
