import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TimePoint } from "@/lib/api";
import { formatEur, formatDateShort } from "@/lib/utils";
import { chartTheme } from "@/lib/chartTheme";

interface PatrimoineChartProps {
  data: TimePoint[];
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
}) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={chartTheme.tooltipStyle} className="px-3 py-2">
      <div className="text-text-muted text-xs mb-0.5">{label}</div>
      <div className="text-text-primary font-semibold text-sm">
        {formatEur(payload[0].value)}
      </div>
    </div>
  );
}

export function PatrimoineChart({ data }: PatrimoineChartProps) {
  const isPositive =
    data.length >= 2
      ? data[data.length - 1].total_eur >= data[0].total_eur
      : true;
  const lineColor = isPositive ? chartTheme.positiveColor : chartTheme.negativeColor;

  const formatted = data.map((p) => ({
    ...p,
    label: formatDateShort(p.ts),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={formatted} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="patrimoine-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={lineColor} stopOpacity={chartTheme.gradientOpacityTop} />
            <stop offset="100%" stopColor={lineColor} stopOpacity={chartTheme.gradientOpacityBottom} />
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
        <Tooltip content={<CustomTooltip />} cursor={{ stroke: chartTheme.gridColor }} />
        <Area
          type="monotone"
          dataKey="total_eur"
          stroke={lineColor}
          strokeWidth={chartTheme.strokeWidth}
          fill="url(#patrimoine-gradient)"
          dot={false}
          activeDot={{ r: 4, fill: lineColor, stroke: "#141720", strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
