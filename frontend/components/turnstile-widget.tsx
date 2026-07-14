"use client";

import { useEffect, useRef } from "react";
import Script from "next/script";

// Free, unlimited challenges, no card (turnstile.com) -- renders nothing when
// unset, same no-op-when-unconfigured pattern as lib/analytics.ts, so
// register/login work identically without a site key configured.
const SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;

declare global {
  interface Window {
    turnstile?: {
      render: (container: HTMLElement, options: Record<string, unknown>) => string;
      reset: (widgetId?: string) => void;
    };
  }
}

export function TurnstileWidget({ onVerify }: { onVerify: (token: string | null) => void }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!SITE_KEY) return;

    function render() {
      if (!containerRef.current || !window.turnstile || widgetIdRef.current) return;
      widgetIdRef.current = window.turnstile.render(containerRef.current, {
        sitekey: SITE_KEY,
        callback: (token: string) => onVerify(token),
        "expired-callback": () => onVerify(null),
        "error-callback": () => onVerify(null),
      });
    }

    if (window.turnstile) {
      render();
      return;
    }
    // The Script tag below loads asynchronously; poll briefly for the global
    // it attaches rather than wiring up Cloudflare's onload=... callback
    // param, which would need a function registered on window before the
    // script tag exists.
    const id = window.setInterval(() => {
      if (window.turnstile) {
        render();
        window.clearInterval(id);
      }
    }, 100);
    return () => window.clearInterval(id);
  }, [onVerify]);

  if (!SITE_KEY) return null;

  return (
    <>
      <Script src="https://challenges.cloudflare.com/turnstile/v0/api.js" strategy="afterInteractive" />
      <div ref={containerRef} className="flex justify-center" />
    </>
  );
}
