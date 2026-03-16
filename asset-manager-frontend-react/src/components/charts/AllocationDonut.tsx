import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { formatEur } from "@/lib/utils";

interface DonutItem {
  key: string;
  value_eur: number;
  pct: number;
}

interface AllocationDonutProps {
  data: DonutItem[];
  colors: Record<string, string>;
  labelMap?: Record<string, string>;
}

function CustomTooltip({ active, payload }: {
  active?: boolean;
  payload?: { name: string; value: number; payload: DonutItem }[];
}) {
  if (!active || !payload || !payload.length) return null;
  const item = payload[0].payload;
  return (
    <div
      className="px-3 py-2 rounded-[10px] text-xs"
      style={{
        background: "#141720",
        border: "1px solid #252a38",
        color: "#f0f2f8",
      }}
    >
      <div className="font-medium">{payload[0].name}</div>
      <div className="text-text-secondary">{formatEur(item.value_eur)}</div>
      <div className="text-text-muted">{item.pct.toFixed(1)}%</div>
    </div>
  );
}

export function AllocationDonut({ data, colors, labelMap }: AllocationDonutProps) {
  const getLabel = (key: string) => (labelMap ? (labelMap[key] ?? key) : key);
  const getColor = (key: string) => colors[key] ?? "#94a3b8";

  return (
    <div>
      <ResponsiveContainer width="100%" height={160}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value_eur"
            nameKey="key"
            cx="50%"
            cy="50%"
            innerRadius={48}
            outerRadius={72}
            strokeWidth={0}
          >
            {data.map((item) => (
              <Cell key={item.key} fill={getColor(item.key)} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>

      {/* Custom legend */}
      <div className="mt-3 space-y-1.5">
        {data.map((item) => (
          <div key={item.key} className="flex items-center gap-2 text-xs">
            <div
              className="w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: getColor(item.key) }}
            />
            <span className="flex-1 text-text-secondary truncate">
              {getLabel(item.key)}
            </span>
            <span className="text-text-primary font-medium tabular-nums">
              {formatEur(item.value_eur)}
            </span>
            <span className="text-text-muted tabular-nums w-10 text-right">
              {item.pct.toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
