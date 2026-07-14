import type { Comp } from "@/lib/types";

export interface DealScore {
  /** 0-100: what fraction of comps this estimate beats on price (lower price = higher score, since a "good deal" means less expensive than the field). */
  percentile: number;
  /** Signed % difference between the estimate midpoint and the comps' median price. */
  vsMedianPct: number;
  label: "Below market" | "At market" | "Above market";
}

/** Deterministic, no LLM involved -- purely a rank of the AVM estimate's
 * midpoint against the comps already fetched for this query. A query with
 * fewer than 2 comps has nothing to rank against, so callers should treat
 * `null` as "not enough data," not "average." */
export function computeDealScore(
  valuationLow: number | null | undefined,
  valuationHigh: number | null | undefined,
  comps: Comp[]
): DealScore | null {
  const prices = comps.map((c) => c.price).filter((p): p is number => typeof p === "number" && p > 0);
  if (prices.length < 2 || valuationLow == null || valuationHigh == null) return null;

  const mid = (valuationLow + valuationHigh) / 2;
  const sorted = [...prices].sort((a, b) => a - b);
  const countBelow = sorted.filter((p) => p < mid).length;
  const countEqual = sorted.filter((p) => p === mid).length;
  // Midpoint rank convention: ties split evenly rather than all counting as "below."
  const percentile = Math.round(((countBelow + countEqual / 2) / sorted.length) * 100);

  const median = sorted.length % 2 === 0
    ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
    : sorted[(sorted.length - 1) / 2];
  const vsMedianPct = median > 0 ? Math.round(((mid - median) / median) * 1000) / 10 : 0;

  const label: DealScore["label"] = vsMedianPct <= -3 ? "Below market" : vsMedianPct >= 3 ? "Above market" : "At market";

  return { percentile, vsMedianPct, label };
}
