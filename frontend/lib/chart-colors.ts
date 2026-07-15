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
  brass: "#E38B4A",
  textPrimary: "#F1EDE5",
  textMuted: "#93A6A3",
  border: "#253F3C",
  positive: "#3FA579",
  negative: "#E0526E",
  surface: "#0F1F1E",
  categorical: ["#C97A3A", "#4A9BD6", "#D65A99", "#5F9A2E"],
  // Legible text color for a filled chip/pill using a `categorical` color as
  // its background (e.g. a selected community filter). Computed per-theme,
  // not fixed white/black -- see the light-mode comment below.
  onCategorical: "#0A1615",
};

const LIGHT = {
  brass: "#9C4E20",
  textPrimary: "#0E1D1B",
  textMuted: "#52706C",
  border: "#D7E1DF",
  positive: "#166B46",
  negative: "#C23B52",
  surface: "#FFFFFF",
  categorical: ["#9C4E20", "#1E6FA8", "#B23A72", "#4F7A1B"],
  onCategorical: "#FFFFFF",
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
