"use client";

import { useLocale } from "@/components/locale-provider";

/** Renders a translated string inside an otherwise-server component, e.g.
 * <h1><T k="home.title" /></h1>. Named `T`, not `Translate`/`Trans`, to
 * stay unobtrusive in JSX-heavy server component markup. */
export function T({ k }: { k: string }) {
  const { t } = useLocale();
  return <>{t(k)}</>;
}
