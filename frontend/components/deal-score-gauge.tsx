"use client";

import { useChartColors } from "@/lib/chart-colors";
import type { DealScore } from "@/lib/deal-score";

const WIDTH = 320;
const HEIGHT = 40;
const TRACK_Y = 20;

/** "Below market" is framed as good for a buyer (positive token), "Above
 * market" as a caution (negative token) -- this is a real status judgment,
 * not an arbitrary series color, so it borrows the same positive/negative
 * tokens the rest of the app already uses for price deltas and provenance. */
export function DealScoreGauge({ score }: { score: DealScore }) {
  const colors = useChartColors();
  const statusColor =
    score.label === "Below market" ? colors.positive : score.label === "Above market" ? colors.negative : colors.brass;

  const fillX = (score.percentile / 100) * WIDTH;

  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-text-muted">Deal score</p>
        <span
          className="rounded-full px-2 py-0.5 text-xs font-medium"
          style={{ color: statusColor, backgroundColor: `${statusColor}1a` }}
        >
          {score.label}
        </span>
      </div>

      <div className="mt-2 flex items-center gap-3" dir="ltr">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-8 flex-1" role="img" aria-label={`${score.percentile}th percentile among comps, ${score.vsMedianPct > 0 ? "+" : ""}${score.vsMedianPct}% vs median`}>
          <rect x={0} y={TRACK_Y - 5} width={WIDTH} height={10} rx={5} fill={colors.border} />
          <rect x={0} y={TRACK_Y - 5} width={Math.max(fillX, 10)} height={10} rx={5} fill={statusColor} />
          <circle cx={fillX} cy={TRACK_Y} r={7} fill={colors.surface} stroke={statusColor} strokeWidth={3} />
        </svg>
        <span className="shrink-0 font-mono text-sm text-text-primary">{score.percentile}th pct</span>
      </div>
      <p className="mt-1 text-xs text-text-muted">
        {score.vsMedianPct > 0 ? "+" : ""}
        {score.vsMedianPct}% vs comps median
      </p>
    </div>
  );
}
