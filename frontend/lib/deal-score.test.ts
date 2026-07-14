import { describe, it, expect } from "vitest";
import { computeDealScore } from "@/lib/deal-score";
import type { Comp } from "@/lib/types";

function comp(price: number): Comp {
  return {
    transaction_id: `TXN-${price}`,
    building: "Test Tower",
    community: "Test Community",
    property_type: "Apartment",
    bedrooms: 2,
    size_sqft: 1000,
    price,
    price_per_sqft: price / 1000,
    date: "2026-01-01",
  };
}

describe("computeDealScore", () => {
  it("returns null with fewer than 2 comps", () => {
    expect(computeDealScore(1_000_000, 1_200_000, [comp(1_100_000)])).toBeNull();
  });

  it("returns null when valuation bounds are missing", () => {
    expect(computeDealScore(null, null, [comp(1_000_000), comp(2_000_000)])).toBeNull();
  });

  it("scores an estimate below all comps as a low percentile / below market", () => {
    const comps = [comp(2_000_000), comp(2_200_000), comp(2_400_000)];
    const score = computeDealScore(1_000_000, 1_200_000, comps); // mid = 1.1M, below all comps
    expect(score).not.toBeNull();
    expect(score!.percentile).toBe(0);
    expect(score!.label).toBe("Below market");
    expect(score!.vsMedianPct).toBeLessThan(0);
  });

  it("scores an estimate above all comps as a high percentile / above market", () => {
    const comps = [comp(1_000_000), comp(1_100_000), comp(1_200_000)];
    const score = computeDealScore(2_000_000, 2_200_000, comps); // mid = 2.1M, above all comps
    expect(score).not.toBeNull();
    expect(score!.percentile).toBe(100);
    expect(score!.label).toBe("Above market");
  });

  it("scores an estimate matching the comps' median as at-market, ~50th percentile", () => {
    const comps = [comp(1_000_000), comp(1_500_000), comp(2_000_000)];
    const score = computeDealScore(1_400_000, 1_600_000, comps); // mid = 1.5M = median
    expect(score).not.toBeNull();
    expect(score!.percentile).toBe(50);
    expect(score!.label).toBe("At market");
    expect(score!.vsMedianPct).toBe(0);
  });

  it("ignores non-positive or missing comp prices", () => {
    const comps: Comp[] = [comp(1_000_000), comp(1_500_000), { ...comp(0), price: 0 }];
    // mid = 1,000,000, which ties the first (real) comp and is below the
    // second -- with the zero-price row correctly excluded, that's a
    // half-tie out of 2 real comps, i.e. the 25th percentile, not the 17th
    // it would be if the bogus zero-price row were counted.
    const score = computeDealScore(900_000, 1_100_000, comps);
    expect(score).not.toBeNull();
    expect(score!.percentile).toBe(25);
  });
});
