"use client";

import { useMemo, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { useChartColors } from "@/lib/chart-colors";
import { buildPriceBins, type PriceBin } from "@/lib/price-distribution";
import type { Comp } from "@/lib/types";

/** Histogram of AED/sqft across the currently filtered comps -- shows the
 * shape of the market (tight cluster vs wide spread) that a flat list or
 * map can't. Self-contained: uses the comps array Comps Explorer already
 * has in state, no new API call. */
export function PriceDistributionChart({ comps }: { comps: Comp[] }) {
  const colors = useChartColors();
  const [showTable, setShowTable] = useState(false);

  const bins = useMemo(
    () => buildPriceBins(comps.map((c) => c.price_per_sqft).filter((p): p is number => typeof p === "number" && p > 0)),
    [comps]
  );

  if (bins.length === 0) {
    return <p className="text-sm text-text-muted">No price data to chart yet.</p>;
  }

  if (showTable) {
    return (
      <div>
        <div className="flex justify-end">
          <button onClick={() => setShowTable(false)} className="text-xs text-text-muted underline decoration-dotted hover:text-text-primary">
            Show chart
          </button>
        </div>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase text-text-muted">
              <th className="py-1.5 font-medium">AED/sqft range</th>
              <th className="py-1.5 font-medium">Comps</th>
            </tr>
          </thead>
          <tbody className="font-mono text-xs">
            {bins.map((b) => (
              <tr key={b.label} className="border-b border-border last:border-0">
                <td className="py-1.5 text-text-primary">
                  {Math.round(b.rangeLow).toLocaleString()} – {Math.round(b.rangeHigh).toLocaleString()}
                </td>
                <td className="py-1.5">{b.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-text-muted">AED/sqft distribution · {comps.length} comps</p>
        <button onClick={() => setShowTable(true)} className="shrink-0 text-xs text-text-muted underline decoration-dotted hover:text-text-primary">
          Show as table
        </button>
      </div>
      <div className="mt-2 h-40" dir="ltr">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={bins} margin={{ left: 0, right: 8, top: 4, bottom: 0 }}>
            <CartesianGrid stroke={colors.border} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" stroke={colors.textMuted} fontSize={10} tickLine={false} axisLine={false} interval={1} />
            <YAxis stroke={colors.textMuted} fontSize={10} tickLine={false} axisLine={false} width={24} allowDecimals={false} />
            <Tooltip
              cursor={{ fill: colors.border, opacity: 0.3 }}
              contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: colors.textPrimary }}
              formatter={(value, _name, item) => {
                const bin = item?.payload as PriceBin;
                return [`${value} comp${value === 1 ? "" : "s"}`, `AED ${Math.round(bin.rangeLow).toLocaleString()}–${Math.round(bin.rangeHigh).toLocaleString()}/sqft`];
              }}
            />
            <Bar dataKey="count" radius={[3, 3, 0, 0]} maxBarSize={28}>
              {bins.map((b) => (
                <Cell key={b.label} fill={colors.brass} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
