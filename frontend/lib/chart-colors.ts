"use client";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

// Mirrors the CSS-variable tokens in app/globals.css (Section 4.3). Recharts
// renders raw SVG and can't consume Tailwind classes/CSS vars directly, so
// the same values are duplicated here as literal hex for both themes.
const DARK = {
  brass: "#C9A227",
  textPrimary: "#EDEFF3",
  textMuted: "#8A94AC",
  border: "#25324A",
  positive: "#2F9E68",
  negative: "#C4573B",
  surface: "#121B2E",
};

const LIGHT = {
  brass: "#A6821E",
  textPrimary: "#101828",
  textMuted: "#5B6478",
  border: "#D8DEE8",
  positive: "#1F7A4D",
  negative: "#A8432B",
  surface: "#FFFFFF",
};

export function useChartColors() {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  // Default to dark (the app's default theme) until mounted, to match SSR.
  return mounted && resolvedTheme === "light" ? LIGHT : DARK;
}
