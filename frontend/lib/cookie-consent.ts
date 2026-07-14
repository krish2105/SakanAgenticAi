"use client";

/** Tri-state consent for analytics tracking, persisted in localStorage.
 * null means "never asked" -- CookieConsentBanner shows until the visitor
 * picks one. Gates lib/analytics.ts's PostHog init: "accepted" is required
 * before any tracking call actually reaches PostHog, not just before the
 * banner disappears. */
const STORAGE_KEY = "sakan_cookie_consent";

export type ConsentValue = "accepted" | "rejected";

export function getCookieConsent(): ConsentValue | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  return raw === "accepted" || raw === "rejected" ? raw : null;
}

export function setCookieConsent(value: ConsentValue): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, value);
}
