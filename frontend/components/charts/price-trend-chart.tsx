"use client";

import { useMemo, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useChartColors } from "@/lib/chart-colors";
import type { MarketTrendPoint } from "@/lib/types";

export function PriceTrendChart({ trends }: { trends: MarketTrendPoint[] }) {
  const colors = useChartColors();
  const communities = useMemo(() => Array.from(new Set(trends.map((t) => t.community))), [trends]);
  const [community, setCommunity] = useState(communities[0] ?? "");
  const [showTable, setShowTable] = useState(false);

  const series = trends
    .filter((t) => t.community === community)
    .sort((a, b) => a.month.localeCompare(b.month));

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label className="flex items-center gap-2 text-xs text-text-muted">
          Community
          <select
            value={community}
            onChange={(e) => setCommunity(e.target.value)}
            className="h-8 rounded-lg border border-border bg-surface px-2 text-sm text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brass"
          >
            {communities.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={() => setShowTable((v) => !v)}
          className="text-xs text-text-muted underline decoration-dotted hover:text-text-primary"
        >
          {showTable ? "Show chart" : "Show as table"}
        </button>
      </div>

      {showTable ? (
        <table className="mt-4 w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase text-text-muted">
              <th className="py-1.5 font-medium">Month</th>
              <th className="py-1.5 font-medium">Avg AED/sqft</th>
            </tr>
          </thead>
          <tbody className="font-mono text-xs">
            {series.map((p) => (
              <tr key={p.month} className="border-b border-border last:border-0">
                <td className="py-1.5">{p.month}</td>
                <td className="py-1.5 text-text-primary">{p.avg_price_per_sqft}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        /* dir="ltr": see the comment in developer-leaderboard-chart.tsx --
           Recharts isn't RTL-aware; kept consistent across all three
           charts even though this one's numeric axes render fine either
           way. */
        <div className="mt-4 h-64" dir="ltr">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ left: 0, right: 12, top: 8, bottom: 0 }}>
              <CartesianGrid stroke={colors.border} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" stroke={colors.textMuted} fontSize={11} tickLine={false} />
              <YAxis
                stroke={colors.textMuted}
                fontSize={11}
                tickLine={false}
                axisLine={false}
                width={56}
                tickFormatter={(v) => `${v}`}
              />
              <Tooltip
                contentStyle={{
                  background: colors.surface,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: colors.textMuted }}
                formatter={(value) => [`AED ${value}`, "avg / sqft"]}
              />
              <Line
                type="monotone"
                dataKey="avg_price_per_sqft"
                stroke={colors.brass}
                strokeWidth={2}
                dot={{ r: 3, fill: colors.brass, strokeWidth: 0 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
