"use client";

import { useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useChartColors } from "@/lib/chart-colors";
import type { DailyUsage } from "@/lib/api";

/** Fills in every day from the 1st of the current month through today with
 * a zero count, so the chart reads as a continuous calendar strip rather
 * than a handful of scattered bars on days with activity. */
function fillMonthToDate(days: DailyUsage[]): DailyUsage[] {
  const counts = new Map(days.map((d) => [d.date, d.count]));
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const out: DailyUsage[] = [];
  for (let d = new Date(start); d <= now; d.setDate(d.getDate() + 1)) {
    const iso = d.toISOString().slice(0, 10);
    out.push({ date: iso, count: counts.get(iso) ?? 0 });
  }
  return out;
}

export function UsageTimeseriesChart({ days }: { days: DailyUsage[] }) {
  const colors = useChartColors();
  const filled = useMemo(() => fillMonthToDate(days), [days]);

  return (
    <div className="mt-4" dir="ltr">
      <p className="text-xs text-text-muted">Full-pipeline queries this month</p>
      <div className="mt-2 h-32">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={filled} margin={{ left: 0, right: 8, top: 4, bottom: 0 }}>
            <CartesianGrid stroke={colors.border} strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              stroke={colors.textMuted}
              fontSize={9}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => String(v).slice(8, 10)}
              interval={Math.max(0, Math.floor(filled.length / 8) - 1)}
            />
            <YAxis stroke={colors.textMuted} fontSize={10} tickLine={false} axisLine={false} width={20} allowDecimals={false} />
            <Tooltip
              cursor={{ fill: colors.border, opacity: 0.3 }}
              contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: colors.textPrimary }}
              formatter={(value) => [`${value} quer${value === 1 ? "y" : "ies"}`, ""]}
            />
            <Bar dataKey="count" fill={colors.brass} radius={[2, 2, 0, 0]} maxBarSize={14} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
