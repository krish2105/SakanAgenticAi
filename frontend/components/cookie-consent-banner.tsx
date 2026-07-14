"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { getCookieConsent, setCookieConsent } from "@/lib/cookie-consent";
import { initAnalytics } from "@/lib/analytics";

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;

/** Nothing to ask consent for when analytics isn't even configured -- same
 * no-op-when-unconfigured posture as the rest of this app. Auth tokens live
 * in localStorage, not cookies, so PostHog is the only thing this consent
 * actually gates today. */
export function CookieConsentBanner() {
  // Starts hidden on both server and client (no hydration mismatch --
  // getCookieConsent() would return null during SSR regardless of the
  // visitor's real, client-only localStorage choice, so reading it in a
  // lazy useState initializer would make server and client disagree for
  // any returning visitor). The real check runs once, client-only, after
  // mount -- nested in a plain function rather than calling setState
  // directly in the effect body, same pattern as admin-client.tsx's
  // gateAndLoad().
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    function checkConsent() {
      if (!POSTHOG_KEY) return;
      setVisible(getCookieConsent() === null);
    }
    checkConsent();
  }, []);

  if (!POSTHOG_KEY || !visible) return null;

  function accept() {
    setCookieConsent("accepted");
    initAnalytics();
    setVisible(false);
  }

  function reject() {
    setCookieConsent("rejected");
    setVisible(false);
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-surface/95 backdrop-blur">
      <div className="mx-auto flex max-w-4xl flex-col items-start gap-3 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-text-muted">
          We use privacy-respecting analytics to understand how Sakan AI is used. No tracking
          until you say yes.{" "}
          <Link href="/legal/privacy" className="text-brass underline">
            Privacy Policy
          </Link>
          .
        </p>
        <div className="flex shrink-0 gap-2">
          <Button variant="outline" size="sm" onClick={reject}>
            Reject
          </Button>
          <Button size="sm" onClick={accept}>
            Accept
          </Button>
        </div>
      </div>
    </div>
  );
}
