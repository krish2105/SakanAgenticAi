import { describe, it, expect } from "vitest";
import { buildPriceBins } from "@/lib/price-distribution";

describe("buildPriceBins", () => {
  it("returns an empty array for no values", () => {
    expect(buildPriceBins([])).toEqual([]);
  });

  it("buckets every value into exactly one bin, preserving the total count", () => {
    const values = [1000, 1200, 1500, 1800, 2000, 2200, 2500, 3000];
    const bins = buildPriceBins(values, 4);
    expect(bins).toHaveLength(4);
    expect(bins.reduce((sum, b) => sum + b.count, 0)).toBe(values.length);
  });

  it("puts the maximum value in the last bin, not off the end", () => {
    const values = [100, 200, 300];
    const bins = buildPriceBins(values, 3);
    expect(bins[bins.length - 1].count).toBeGreaterThanOrEqual(1);
    expect(bins.reduce((sum, b) => sum + b.count, 0)).toBe(3);
  });

  it("handles every value being identical without dividing by zero", () => {
    const bins = buildPriceBins([1500, 1500, 1500], 4);
    expect(bins).toHaveLength(4);
    expect(bins.reduce((sum, b) => sum + b.count, 0)).toBe(3);
    // All identical values collapse into the first bin's zero-width range.
    expect(bins[0].count).toBe(3);
  });

  it("labels each bin with its rounded lower bound", () => {
    const bins = buildPriceBins([1000, 2000], 2);
    expect(bins[0].label).toBe(bins[0].rangeLow.toLocaleString());
  });
});
