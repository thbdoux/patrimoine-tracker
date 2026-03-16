import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { StackedPoint } from "@/lib/api";
import { formatEur, formatDateShort, ACCOUNT_TYPE_COLORS, ACCOUNT_TYPE_LABELS } from "@/lib/utils";
import { chartTheme } from "@/lib/chartTheme";

interface StackedAreaChartProps {
  data: StackedPoint[];
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { name: string; value: number; fill: string }[];
  label?: string;
}) {
  if (!active || !payload || !payload.length) return null;
  const total = payload.reduce((sum, p) => sum + (p.value || 0), 0);
  return (
    <div style={chartTheme.tooltipStyle} className="px-3 py-2 min-w-[180px]">
      <div className="text-text-muted text-xs mb-1.5">{label}</div>
      <div className="text-text-primary font-semibold text-sm mb-1.5">{formatEur(total)}</div>
      {[...payload].reverse().map((p) => (
        <div key={p.name} className="flex items-center justify-between gap-3 text-xs py-0.5">
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full" style={{ background: p.fill }} />
            <span className="text-text-secondary">{ACCOUNT_TYPE_LABELS[p.name] ?? p.name}</span>
          </div>
          <span className="text-text-primary tabular-nums">{formatEur(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

export function StackedAreaChart({ data }: StackedAreaChartProps) {
  if (!data.length) return null;

  const keys = Object.keys(data[0]).filter((k) => k !== "ts");
  const formatted = data.map((p) => ({
    ...p,
    label: formatDateShort(p.ts),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={formatted} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <defs>
          {keys.map((key) => (
            <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="0%"
                stopColor={ACCOUNT_TYPE_COLORS[key] ?? "#94a3b8"}
                stopOpacity={0.5}
              />
              <stop
                offset="100%"
                stopColor={ACCOUNT_TYPE_COLORS[key] ?? "#94a3b8"}
                stopOpacity={0.1}
              />
            </linearGradient>
          ))}
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
        <Tooltip content={<CustomTooltip />} cursor={{ stroke: chartTheme.gridColor }} />
        {keys.map((key) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            stackId="1"
            stroke={ACCOUNT_TYPE_COLORS[key] ?? "#94a3b8"}
            strokeWidth={1}
            fill={`url(#grad-${key})`}
            dot={false}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
