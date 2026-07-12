"use client";
import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  // SSR-hydration guard (next-themes' own recommended pattern), not a bug.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="h-9 w-9" />;

  return (
    <button
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      aria-label="Toggle theme"
      className="h-9 w-9 rounded-full border border-border bg-surface
                 flex items-center justify-center transition-colors
                 hover:border-brass focus-visible:outline-none
                 focus-visible:ring-2 focus-visible:ring-brass"
    >
      {theme === "dark" ? (
        <Sun size={16} className="text-brass" />
      ) : (
        <Moon size={16} className="text-brass" />
      )}
    </button>
  );
}
