"use client";

import { X } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { useChartColors } from "@/lib/chart-colors";
import type { Comp } from "@/lib/types";

const ROWS: { key: keyof Comp; label: string; format?: (v: unknown) => string }[] = [
  { key: "community", label: "Community" },
  { key: "property_type", label: "Type" },
  { key: "bedrooms", label: "Bedrooms" },
  { key: "size_sqft", label: "Size (sqft)", format: (v) => (v as number)?.toLocaleString() },
  { key: "price", label: "Price", format: (v) => `AED ${(v as number)?.toLocaleString()}` },
  { key: "price_per_sqft", label: "AED/sqft", format: (v) => (v as number)?.toLocaleString() },
  { key: "date", label: "Sale date" },
];

/** Side-by-side comparison of 2-4 comps the user picked in Comps Explorer.
 * Reuses command-palette.tsx's hand-rolled overlay pattern rather than a
 * generic Dialog primitive -- this is the second and, so far, only other
 * modal in the app, not worth abstracting yet. */
export function CompComparisonModal({ comps, onClose }: { comps: Comp[]; onClose: () => void }) {
  const colors = useChartColors();
  const chartData = comps.map((c, i) => ({
    label: c.building.length > 14 ? `${c.building.slice(0, 14)}…` : c.building,
    price_per_sqft: c.price_per_sqft,
    colorIndex: i,
  }));

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 pt-[8vh] backdrop-blur-sm"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="w-full max-w-3xl overflow-hidden rounded-xl border border-border bg-surface shadow-2xl shadow-black/20"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Compare comps"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <h2 className="font-display text-base font-semibold text-text-primary">Compare {comps.length} comps</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close comparison"
            className="rounded p-1 text-text-muted hover:bg-border/40 hover:text-text-primary"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-5">
          <p className="text-xs text-text-muted">AED/sqft</p>
          <div className="mt-2 h-40" dir="ltr">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ left: 0, right: 8, top: 4, bottom: 0 }}>
                <CartesianGrid stroke={colors.border} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" stroke={colors.textMuted} fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke={colors.textMuted} fontSize={10} tickLine={false} axisLine={false} width={44} />
                <Tooltip
                  cursor={{ fill: colors.border, opacity: 0.3 }}
                  contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: colors.textPrimary }}
                  formatter={(value) => [`AED ${value}`, "per sqft"]}
                />
                <Bar dataKey="price_per_sqft" radius={[3, 3, 0, 0]} maxBarSize={48}>
                  {chartData.map((d) => (
                    <Cell key={d.label} fill={colors.categorical[d.colorIndex % colors.categorical.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-5 overflow-x-auto" tabIndex={0} role="region" aria-label="Comparison table">
            <table className="w-full min-w-[480px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-text-muted">
                  <th className="py-2 pr-3 font-medium"> </th>
                  {comps.map((c, i) => (
                    <th key={c.transaction_id} className="py-2 pr-3 font-medium">
                      <span
                        className="me-1.5 inline-block h-2 w-2 rounded-full align-middle"
                        style={{ backgroundColor: colors.categorical[i % colors.categorical.length] }}
                      />
                      {c.building}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="font-mono text-xs">
                {ROWS.map((row) => (
                  <tr key={String(row.key)} className="border-b border-border last:border-0">
                    <td className="py-2 pr-3 font-body text-text-muted">{row.label}</td>
                    {comps.map((c) => (
                      <td key={c.transaction_id} className="py-2 pr-3 text-text-primary">
                        {row.format ? row.format(c[row.key]) : String(c[row.key] ?? "—")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
