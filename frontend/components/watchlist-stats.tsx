"use client";

import { useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { useChartColors } from "@/lib/chart-colors";
import type { Comp } from "@/lib/types";

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <p className="text-xs text-text-muted">{label}</p>
      <p className="mt-1 font-mono-nums text-2xl font-medium text-text-primary">{value}</p>
    </div>
  );
}

/** Aggregate view of the watchlist: three headline stats (a chart would be
 * overkill for a single number -- see dataviz's "sometimes the answer is
 * not a chart") plus a small breakdown of which communities the saved comps
 * come from, which IS a real magnitude comparison across categories. */
export function WatchlistStats({ comps }: { comps: Comp[] }) {
  const colors = useChartColors();

  const { totalValue, avgPricePerSqft, byCommunity } = useMemo(() => {
    const prices = comps.map((c) => c.price).filter((p): p is number => typeof p === "number");
    const pps = comps.map((c) => c.price_per_sqft).filter((p): p is number => typeof p === "number");
    const counts = new Map<string, number>();
    for (const c of comps) counts.set(c.community, (counts.get(c.community) ?? 0) + 1);
    return {
      totalValue: prices.reduce((s, p) => s + p, 0),
      avgPricePerSqft: pps.length ? pps.reduce((s, p) => s + p, 0) / pps.length : 0,
      byCommunity: Array.from(counts.entries())
        .map(([community, count]) => ({ community, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 8),
    };
  }, [comps]);

  if (comps.length === 0) return null;

  return (
    <div className="mb-6">
      <div className="grid grid-cols-3 gap-3">
        <StatTile label="Saved comps" value={String(comps.length)} />
        <StatTile label="Total value" value={`AED ${Math.round(totalValue).toLocaleString()}`} />
        <StatTile label="Avg AED/sqft" value={Math.round(avgPricePerSqft).toLocaleString()} />
      </div>

      {byCommunity.length > 1 && (
        <div className="mt-3 rounded-xl border border-border bg-surface p-4">
          <p className="text-xs text-text-muted">Communities represented</p>
          <div className="mt-2" dir="ltr" style={{ height: byCommunity.length * 28 + 16 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byCommunity} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
                <CartesianGrid stroke={colors.border} strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" allowDecimals={false} stroke={colors.textMuted} fontSize={10} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="community" stroke={colors.textMuted} fontSize={11} tickLine={false} axisLine={false} width={130} />
                <Tooltip
                  cursor={{ fill: colors.border, opacity: 0.3 }}
                  contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: colors.textPrimary }}
                  formatter={(value) => [`${value} comp${value === 1 ? "" : "s"}`, ""]}
                />
                <Bar dataKey="count" radius={[0, 3, 3, 0]} maxBarSize={16}>
                  {byCommunity.map((row) => (
                    <Cell key={row.community} fill={colors.brass} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
