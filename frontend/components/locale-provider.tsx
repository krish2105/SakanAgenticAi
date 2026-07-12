"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { DICTIONARIES, dirFor, translate, type Locale } from "@/lib/i18n";

const LOCALE_STORAGE_KEY = "sakan_locale";

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: keyof (typeof DICTIONARIES)["en"] | string) => string;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    async function restoreLocale() {
      const stored = typeof window !== "undefined" ? localStorage.getItem(LOCALE_STORAGE_KEY) : null;
      if (stored === "en" || stored === "ar") {
        setLocaleState(stored);
      }
    }
    restoreLocale();
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = dirFor(locale);
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    localStorage.setItem(LOCALE_STORAGE_KEY, next);
    setLocaleState(next);
  }, []);

  const t = useCallback((key: string) => translate(locale, key), [locale]);

  return <LocaleContext.Provider value={{ locale, setLocale, t }}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within LocaleProvider");
  return ctx;
}
