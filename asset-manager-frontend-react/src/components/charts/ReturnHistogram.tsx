import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { ReturnPoint } from "@/lib/api";
import { chartTheme } from "@/lib/chartTheme";

interface ReturnHistogramProps {
  data: ReturnPoint[];
}

function buildHistogram(data: ReturnPoint[]) {
  if (!data.length) return [];
  const values = data.map((d) => d.return_pct);
  const min = Math.floor(Math.min(...values) * 10) / 10;
  const max = Math.ceil(Math.max(...values) * 10) / 10;
  const binWidth = (max - min) / 30;

  const bins: { bin: number; count: number }[] = [];
  for (let i = 0; i < 30; i++) {
    const binStart = min + i * binWidth;
    bins.push({
      bin: Math.round(binStart * 100) / 100,
      count: values.filter((v) => v >= binStart && v < binStart + binWidth).length,
    });
  }
  return bins;
}

function CustomTooltip({ active, payload }: {
  active?: boolean;
  payload?: { payload: { bin: number; count: number } }[];
}) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div style={chartTheme.tooltipStyle} className="px-3 py-2">
      <div className="text-text-muted text-xs">{d.bin >= 0 ? "+" : ""}{d.bin.toFixed(2)}%</div>
      <div className="text-text-primary font-semibold">{d.count} jour{d.count > 1 ? "s" : ""}</div>
    </div>
  );
}

export function ReturnHistogram({ data }: ReturnHistogramProps) {
  const bins = buildHistogram(data);

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={bins} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={chartTheme.gridColor} strokeDasharray="0" vertical={false} />
        <XAxis
          dataKey="bin"
          tick={chartTheme.tickStyle}
          axisLine={false}
          tickLine={false}
          interval={5}
          tickFormatter={(v) => `${Number(v) >= 0 ? "+" : ""}${Number(v).toFixed(1)}%`}
        />
        <YAxis
          tick={chartTheme.tickStyle}
          axisLine={false}
          tickLine={false}
          width={30}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
        <Bar dataKey="count" radius={[3, 3, 0, 0]}>
          {bins.map((entry, index) => (
            <Cell
              key={index}
              fill={entry.bin >= 0 ? chartTheme.positiveColor : chartTheme.negativeColor}
              fillOpacity={0.8}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
