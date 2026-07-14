export interface PriceBin {
  label: string;
  rangeLow: number;
  rangeHigh: number;
  count: number;
}

/** Buckets a list of AED/sqft values into `binCount` equal-width bins for a
 * histogram. Pulled out of the chart component so the binning math (which
 * has real edge cases -- empty input, a single repeated value, the
 * max-value boundary) is unit-testable independent of rendering. */
export function buildPriceBins(values: number[], binCount = 8): PriceBin[] {
  if (values.length === 0) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const width = span / binCount;

  const bins: PriceBin[] = Array.from({ length: binCount }, (_, i) => {
    const rangeLow = min + i * width;
    const rangeHigh = i === binCount - 1 ? max : rangeLow + width;
    return { label: `${Math.round(rangeLow).toLocaleString()}`, rangeLow, rangeHigh, count: 0 };
  });

  for (const v of values) {
    const idx = Math.min(binCount - 1, Math.floor(((v - min) / span) * binCount));
    bins[idx].count += 1;
  }
  return bins;
}
