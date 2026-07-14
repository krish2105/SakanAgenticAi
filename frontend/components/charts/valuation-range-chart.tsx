"use client";

import { useId, useMemo, useState } from "react";
import { useChartColors } from "@/lib/chart-colors";
import type { Comp } from "@/lib/types";

const WIDTH = 640;
const HEIGHT = 96;
const PAD_X = 48;
const TRACK_Y = 44;
const BAND_HEIGHT = 14;
const DOT_Y = 74;
const DOT_R = 5;

function fmtAed(v: number): string {
  return `AED ${Math.round(v).toLocaleString()}`;
}

/** A single-axis range-plus-distribution strip: the AVM's [low, high]
 * estimate as a band with the actual comp prices plotted as dots on the
 * same scale, so it's immediately visible whether the estimate is grounded
 * in the real comps or an outlier. Hand-rolled SVG rather than recharts --
 * recharts has no clean primitive for "one axis, a floating range band, and
 * a scatter of points," and the mark count here is small enough that a
 * direct SVG gives more control over the anatomy (rounded band ends, dot
 * sizing) than fighting a bar+scatter composition would. */
export function ValuationRangeChart({
  low,
  high,
  comps,
}: {
  low: number;
  high: number;
  comps: Pick<Comp, "price" | "building">[];
}) {
  const colors = useChartColors();
  const gradientId = useId();
  const [showTable, setShowTable] = useState(false);
  const [hovered, setHovered] = useState<number | null>(null);

  const prices = comps.map((c) => c.price).filter((p) => typeof p === "number" && p > 0);
  const mid = (low + high) / 2;

  const { min, max } = useMemo(() => {
    const all = [low, high, ...prices];
    const lo = Math.min(...all);
    const hi = Math.max(...all);
    const span = hi - lo || 1;
    // 8% breathing room on each side so edge marks aren't clipped.
    return { min: lo - span * 0.08, max: hi + span * 0.08 };
  }, [low, high, prices]);

  const scale = (v: number) => PAD_X + ((v - min) / (max - min)) * (WIDTH - PAD_X * 2);

  if (showTable) {
    return (
      <TableView low={low} high={high} comps={comps} onShowChart={() => setShowTable(false)} />
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-text-muted">
          Estimate <span className="font-mono text-text-primary">{fmtAed(low)}</span> –{" "}
          <span className="font-mono text-text-primary">{fmtAed(high)}</span> against {prices.length} comp
          {prices.length === 1 ? "" : "s"}
        </p>
        <button
          onClick={() => setShowTable(true)}
          className="shrink-0 text-xs text-text-muted underline decoration-dotted hover:text-text-primary"
        >
          Show as table
        </button>
      </div>

      <div className="mt-2" dir="ltr">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-24 w-full" role="img" aria-label={`Valuation range ${fmtAed(low)} to ${fmtAed(high)}, plotted against ${prices.length} comparable prices`}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={colors.brass} stopOpacity="0.35" />
              <stop offset="100%" stopColor={colors.brass} stopOpacity="0.55" />
            </linearGradient>
          </defs>

          {/* Recessive baseline track. */}
          <line x1={PAD_X} y1={TRACK_Y} x2={WIDTH - PAD_X} y2={TRACK_Y} stroke={colors.border} strokeWidth={2} strokeLinecap="round" />

          {/* Estimate range band, rounded ends. */}
          <rect
            x={scale(low)}
            y={TRACK_Y - BAND_HEIGHT / 2}
            width={Math.max(scale(high) - scale(low), 2)}
            height={BAND_HEIGHT}
            rx={BAND_HEIGHT / 2}
            fill={`url(#${gradientId})`}
          />
          {/* Midpoint tick -- the actual point estimate. */}
          <line x1={scale(mid)} y1={TRACK_Y - BAND_HEIGHT} x2={scale(mid)} y2={TRACK_Y + BAND_HEIGHT} stroke={colors.brass} strokeWidth={2} strokeLinecap="round" />

          {/* Comp price dots. */}
          {comps.map((c, i) => {
            if (!(typeof c.price === "number" && c.price > 0)) return null;
            const x = scale(c.price);
            const isHovered = hovered === i;
            return (
              <g key={i}>
                <line x1={x} y1={TRACK_Y + 2} x2={x} y2={DOT_Y - DOT_R} stroke={colors.border} strokeWidth={1} />
                <circle
                  cx={x}
                  cy={DOT_Y}
                  r={isHovered ? DOT_R + 1.5 : DOT_R}
                  fill={colors.surface}
                  stroke={colors.textMuted}
                  strokeWidth={2}
                  className="cursor-pointer transition-all"
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered((h) => (h === i ? null : h))}
                >
                  <title>
                    {c.building}: {fmtAed(c.price)}
                  </title>
                </circle>
              </g>
            );
          })}

          {/* Direct min/max labels. */}
          <text x={PAD_X} y={HEIGHT - 4} fontSize="11" fill={colors.textMuted} textAnchor="start" className="font-mono-nums">
            {fmtAed(min)}
          </text>
          <text x={WIDTH - PAD_X} y={HEIGHT - 4} fontSize="11" fill={colors.textMuted} textAnchor="end" className="font-mono-nums">
            {fmtAed(max)}
          </text>
        </svg>
      </div>
    </div>
  );
}

function TableView({
  low,
  high,
  comps,
  onShowChart,
}: {
  low: number;
  high: number;
  comps: Pick<Comp, "price" | "building">[];
  onShowChart: () => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-text-muted">Estimate vs comps</p>
        <button onClick={onShowChart} className="text-xs text-text-muted underline decoration-dotted hover:text-text-primary">
          Show chart
        </button>
      </div>
      <table className="mt-2 w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase text-text-muted">
            <th className="py-1.5 font-medium">Item</th>
            <th className="py-1.5 font-medium">Price (AED)</th>
          </tr>
        </thead>
        <tbody className="font-mono text-xs">
          <tr className="border-b border-border">
            <td className="py-1.5 text-text-primary">Estimate low</td>
            <td className="py-1.5">{fmtAed(low)}</td>
          </tr>
          <tr className="border-b border-border">
            <td className="py-1.5 text-text-primary">Estimate high</td>
            <td className="py-1.5">{fmtAed(high)}</td>
          </tr>
          {comps.map((c, i) => (
            <tr key={i} className="border-b border-border last:border-0">
              <td className="py-1.5 text-text-muted">{c.building}</td>
              <td className="py-1.5">{fmtAed(c.price)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
