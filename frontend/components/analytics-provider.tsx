"use client";

import { Suspense, useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { initAnalytics, capturePageview } from "@/lib/analytics";

/** useSearchParams() requires a Suspense boundary during production builds
 * (Next.js docs: "Missing Suspense boundary with useSearchParams"). Isolated
 * into its own tiny component so it can't block/suspend the actual page
 * content in `children` -- only the pageview-tracking side effect suspends. */
function PageviewTracker() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (!pathname) return;
    const query = searchParams.toString();
    capturePageview(query ? `${pathname}?${query}` : pathname);
  }, [pathname, searchParams]);

  return null;
}

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    initAnalytics();
  }, []);

  return (
    <>
      <Suspense fallback={null}>
        <PageviewTracker />
      </Suspense>
      {children}
    </>
  );
}
