"use client";
import { useEffect, useState } from "react";
import { Languages } from "lucide-react";
import { useLocale } from "@/components/locale-provider";

export function LocaleToggle() {
  const { locale, setLocale } = useLocale();
  const [mounted, setMounted] = useState(false);
  // SSR-hydration guard, same pattern as components/theme-toggle.tsx.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="h-9 w-9" />;

  return (
    <button
      onClick={() => setLocale(locale === "en" ? "ar" : "en")}
      aria-label={locale === "en" ? "Switch to Arabic" : "التبديل إلى الإنجليزية"}
      className="flex h-9 items-center gap-1.5 rounded-full border border-border bg-surface
                 px-3 text-xs font-medium text-text-primary transition-colors
                 hover:border-brass focus-visible:outline-none
                 focus-visible:ring-2 focus-visible:ring-brass"
    >
      <Languages size={14} className="text-brass" />
      {locale === "en" ? "AR" : "EN"}
    </button>
  );
}
