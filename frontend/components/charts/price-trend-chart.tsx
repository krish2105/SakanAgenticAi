"use client";

import { useMemo, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useChartColors } from "@/lib/chart-colors";
import { cn } from "@/lib/utils";
import type { MarketTrendPoint } from "@/lib/types";

const MAX_COMPARE = 4;

/** Pivots {community, month, avg_price_per_sqft} rows into one row per
 * month with a column per selected community, which is what recharts needs
 * to draw multiple <Line>s sharing an X axis. */
function pivotByMonth(trends: MarketTrendPoint[], communities: string[]) {
  const byMonth = new Map<string, Record<string, string | number>>();
  for (const t of trends) {
    if (!communities.includes(t.community)) continue;
    const row = byMonth.get(t.month) ?? { month: t.month };
    row[t.community] = t.avg_price_per_sqft;
    byMonth.set(t.month, row);
  }
  return Array.from(byMonth.values()).sort((a, b) => String(a.month).localeCompare(String(b.month)));
}

export function PriceTrendChart({ trends }: { trends: MarketTrendPoint[] }) {
  const colors = useChartColors();
  const communities = useMemo(() => Array.from(new Set(trends.map((t) => t.community))).sort(), [trends]);
  const [selected, setSelected] = useState<string[]>(() => (communities[0] ? [communities[0]] : []));
  const [showTable, setShowTable] = useState(false);

  function toggle(community: string) {
    setSelected((prev) => {
      if (prev.includes(community)) return prev.filter((c) => c !== community);
      if (prev.length >= MAX_COMPARE) return prev; // cap concurrent comparisons at the palette size
      return [...prev, community];
    });
  }

  // Color follows the entity for as long as it stays selected: assigned by
  // position within the *current* selection (guaranteed <= MAX_COMPARE, so
  // always distinct), not by its rank in the full community list.
  const colorFor = (community: string) => colors.categorical[selected.indexOf(community) % colors.categorical.length];

  const pivoted = useMemo(() => pivotByMonth(trends, selected), [trends, selected]);

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-wrap gap-1.5">
          {communities.map((c) => {
            const isSelected = selected.includes(c);
            const disabled = !isSelected && selected.length >= MAX_COMPARE;
            return (
              <button
                key={c}
                type="button"
                onClick={() => toggle(c)}
                disabled={disabled}
                aria-pressed={isSelected}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-40",
                  isSelected ? "border-transparent" : "border-border bg-surface text-text-muted hover:text-text-primary"
                )}
                style={isSelected ? { backgroundColor: colorFor(c), color: colors.onCategorical } : undefined}
              >
                {c}
              </button>
            );
          })}
        </div>
        <button
          onClick={() => setShowTable((v) => !v)}
          className="shrink-0 text-xs text-text-muted underline decoration-dotted hover:text-text-primary"
        >
          {showTable ? "Show chart" : "Show as table"}
        </button>
      </div>
      {selected.length >= MAX_COMPARE && (
        <p className="mt-1 text-xs text-text-muted">Comparing {MAX_COMPARE} communities (the max at once) -- deselect one to swap.</p>
      )}

      {showTable ? (
        <div className="mt-4 overflow-x-auto" tabIndex={0} role="region" aria-label="Price trend table">
          <table className="w-full min-w-[420px] text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase text-text-muted">
                <th className="py-1.5 font-medium">Month</th>
                {selected.map((c) => (
                  <th key={c} className="py-1.5 font-medium">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="font-mono text-xs">
              {pivoted.map((row) => (
                <tr key={String(row.month)} className="border-b border-border last:border-0">
                  <td className="py-1.5">{row.month}</td>
                  {selected.map((c) => (
                    <td key={c} className="py-1.5 text-text-primary">
                      {row[c] != null ? Math.round(Number(row[c])).toLocaleString() : "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* dir="ltr": see the comment in developer-leaderboard-chart.tsx --
           Recharts isn't RTL-aware; kept consistent across all three
           charts even though this one's numeric axes render fine either
           way. */
        <div className="mt-4 h-64" dir="ltr">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={pivoted} margin={{ left: 0, right: 12, top: 8, bottom: 0 }}>
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
                formatter={(value, name) => [`AED ${value}`, name as string]}
              />
              {selected.map((c) => (
                <Line
                  key={c}
                  type="monotone"
                  dataKey={c}
                  name={c}
                  stroke={colorFor(c)}
                  strokeWidth={2}
                  dot={{ r: 3, fill: colorFor(c), strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
