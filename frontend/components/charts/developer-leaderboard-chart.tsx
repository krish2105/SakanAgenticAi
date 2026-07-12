"use client";

import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { useChartColors } from "@/lib/chart-colors";
import type { DeveloperLeaderboardEntry } from "@/lib/types";

export function DeveloperLeaderboardChart({ developers }: { developers: DeveloperLeaderboardEntry[] }) {
  const colors = useChartColors();
  const [showTable, setShowTable] = useState(false);
  const sorted = [...developers].sort((a, b) => b.track_record_score - a.track_record_score).slice(0, 10);

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
              <th className="py-1.5 font-medium">Developer</th>
              <th className="py-1.5 font-medium">Track record</th>
              <th className="py-1.5 font-medium">Active projects</th>
              <th className="py-1.5 font-medium">Delay rate</th>
            </tr>
          </thead>
          <tbody className="font-mono text-xs">
            {sorted.map((d) => (
              <tr key={d.developer_id} className="border-b border-border last:border-0">
                <td className="py-1.5 font-body text-text-primary">{d.name}</td>
                <td className="py-1.5">{d.track_record_score}</td>
                <td className="py-1.5">{d.active_projects_count}</td>
                <td className="py-1.5">{Math.round(d.delivery_delay_rate * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        /* dir="ltr": Recharts isn't RTL-aware -- its category-axis label
           layout overlaps the bars under an inherited dir="rtl" (caught
           via an actual Arabic-mode screenshot, not assumed). Keeping
           data visualizations LTR even inside an RTL page is standard
           practice for numeric charts, not a workaround. */
        <div className="mt-4" dir="ltr" style={{ height: sorted.length * 34 + 20 }}>
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
                width={130}
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
                formatter={(value) => [value as number, "track-record score"]}
              />
              <Bar dataKey="track_record_score" radius={[0, 4, 4, 0]} maxBarSize={18}>
                {sorted.map((d) => (
                  <Cell key={d.developer_id} fill={colors.brass} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
