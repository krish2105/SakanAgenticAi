"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useChartColors } from "@/lib/chart-colors";
import type { AdminQueryVolumeDay } from "@/lib/api";

export function QueryVolumeChart({ data }: { data: AdminQueryVolumeDay[] }) {
  const colors = useChartColors();

  if (data.length === 0) {
    return <p className="py-8 text-center text-sm text-text-muted">No deal queries in this window yet.</p>;
  }

  return (
    // dir="ltr": Recharts isn't RTL-aware -- matches the other charts in this codebase.
    <div className="h-56" dir="ltr">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ left: 0, right: 12, top: 8, bottom: 0 }}>
          <CartesianGrid stroke={colors.border} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="day" stroke={colors.textMuted} fontSize={11} tickLine={false} />
          <YAxis
            stroke={colors.textMuted}
            fontSize={11}
            tickLine={false}
            axisLine={false}
            width={32}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              background: colors.surface,
              border: `1px solid ${colors.border}`,
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: colors.textMuted }}
            formatter={(value) => [value, "queries"]}
          />
          <Bar dataKey="count" fill={colors.brass} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
