"use client";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

// Mirrors the CSS-variable tokens in app/globals.css (Section 4.3). Recharts
// renders raw SVG and can't consume Tailwind classes/CSS vars directly, so
// the same values are duplicated here as literal hex for both themes.
// categorical: a fixed-order 4-hue set for multi-series charts (e.g. the
// community comparison overlay). Slot 0 is a *categorical-safe* variant of
// brass, not the single-series `brass` token above -- the plain brass value
// sits outside dataviz's dark-mode OKLCH lightness band (0.48-0.67) once
// it's competing against 3 other series instead of standing alone, so it's
// darkened slightly here. Validated with the dataviz skill's
// scripts/validate_palette.js (lightness band, chroma floor, CVD adjacent-pair
// separation, contrast vs surface) for both modes before use -- do not edit
// these without re-running that validator.
const DARK = {
  brass: "#C9A227",
  textPrimary: "#EDEFF3",
  textMuted: "#8A94AC",
  border: "#25324A",
  positive: "#2F9E68",
  negative: "#C4573B",
  surface: "#121B2E",
  categorical: ["#AD8A1E", "#4A87BF", "#C0568F", "#739E2C"],
};

const LIGHT = {
  brass: "#A6821E",
  textPrimary: "#101828",
  textMuted: "#5B6478",
  border: "#D8DEE8",
  positive: "#1F7A4D",
  negative: "#A8432B",
  surface: "#FFFFFF",
  categorical: ["#A6821E", "#2E6BA8", "#C23B7A", "#5B8C1F"],
};

export function useChartColors() {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  // SSR-hydration guard, same pattern as components/theme-toggle.tsx.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);
  // Default to dark (the app's default theme) until mounted, to match SSR.
  return mounted && resolvedTheme === "light" ? LIGHT : DARK;
}
