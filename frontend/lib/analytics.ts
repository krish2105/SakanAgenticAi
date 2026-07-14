"use client";

/** Thin PostHog wrapper -- every export is a safe no-op when
 * NEXT_PUBLIC_POSTHOG_KEY is unset, matching this codebase's pattern of
 * degrading gracefully without external config (see lib/api.ts's demo-data
 * fallback, app/services/email.py's console provider, etc.). Nothing else in
 * the app should import "posthog-js" directly -- go through this module so
 * that "analytics unconfigured" stays a single, obvious no-op path. */
import posthog from "posthog-js";
import { getCookieConsent } from "@/lib/cookie-consent";

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com";

let initialized = false;

/** Requires both a configured key AND explicit "accepted" consent --
 * CookieConsentBanner is the only thing that can flip consent to
 * "accepted", so no tracking call reaches PostHog before a visitor has
 * actually said yes (Phase 17: this is the enforcement, not just the
 * banner UI). */
function analyticsAllowed(): boolean {
  return Boolean(POSTHOG_KEY) && getCookieConsent() === "accepted";
}

export function initAnalytics(): void {
  if (!analyticsAllowed() || initialized) return;
  posthog.init(POSTHOG_KEY as string, {
    api_host: POSTHOG_HOST,
    person_profiles: "identified_only",
    capture_pageview: false, // captured manually on route change -- see analytics-provider.tsx
  });
  initialized = true;
}

export function capture(event: string, properties?: Record<string, unknown>): void {
  if (!analyticsAllowed()) return;
  posthog.capture(event, properties);
}

export function capturePageview(url: string): void {
  if (!analyticsAllowed()) return;
  posthog.capture("$pageview", { $current_url: url });
}

export function identifyUser(userId: string | number, properties?: Record<string, unknown>): void {
  if (!analyticsAllowed()) return;
  posthog.identify(String(userId), properties);
}

export function resetAnalytics(): void {
  if (!POSTHOG_KEY) return;
  posthog.reset();
}
