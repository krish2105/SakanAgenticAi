"use client";

import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { useChartColors } from "@/lib/chart-colors";
import type { OffPlanFunnelEntry } from "@/lib/types";

export function OffPlanFunnelChart({ projects }: { projects: OffPlanFunnelEntry[] }) {
  const colors = useChartColors();
  const [showTable, setShowTable] = useState(false);
  const sorted = [...projects].sort((a, b) => b.percent_sold - a.percent_sold).slice(0, 10);

  return (
    <div>
      <div className="flex justify-end">
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
              <th className="py-1.5 font-medium">Project</th>
              <th className="py-1.5 font-medium">Community</th>
              <th className="py-1.5 font-medium">% Sold</th>
            </tr>
          </thead>
          <tbody className="font-mono text-xs">
            {sorted.map((p) => (
              <tr key={p.project_id} className="border-b border-border last:border-0">
                <td className="py-1.5 font-body text-text-primary">{p.name}</td>
                <td className="py-1.5 font-body text-text-muted">{p.community}</td>
                <td className="py-1.5">{p.percent_sold}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="mt-4" style={{ height: sorted.length * 34 + 20 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={sorted} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
              <CartesianGrid stroke={colors.border} strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} stroke={colors.textMuted} fontSize={11} tickLine={false} axisLine={false} />
              <YAxis
                type="category"
                dataKey="name"
                stroke={colors.textMuted}
                fontSize={11}
                tickLine={false}
                axisLine={false}
                width={150}
              />
              <Tooltip
                cursor={{ fill: colors.border, opacity: 0.3 }}
                contentStyle={{
                  background: colors.surface,
                  border: `1px solid ${colors.border}`,
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: colors.textPrimary }}
                formatter={(value) => [`${value}%`, "sold"]}
              />
              <Bar dataKey="percent_sold" radius={[0, 4, 4, 0]} maxBarSize={18}>
                {sorted.map((p) => (
                  <Cell key={p.project_id} fill={colors.brass} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
