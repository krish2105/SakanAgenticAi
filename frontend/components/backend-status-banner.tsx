"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

/** Polls the backend's liveness endpoint and shows an explicit banner when it's
 * unreachable. This is the honest counterpart to the demo-data fallbacks in
 * lib/api.ts: public pages still render (with sample data) during an outage,
 * but the user is now told that's what's happening instead of being silently
 * shown stale/fake numbers as if they were live.
 *
 * Free-tier tolerant: the backend spins down after inactivity and a cold start
 * can take ~50s, so the banner only appears after two consecutive failed polls
 * to avoid flapping during a normal wake-up. */
export function BackendStatusBanner() {
  const [down, setDown] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let failures = 0;

    async function poll() {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 8000);
        const res = await fetch(`${API_BASE}/healthz`, {
          signal: controller.signal,
          cache: "no-store",
        });
        clearTimeout(timer);
        if (!res.ok) throw new Error(String(res.status));
        failures = 0;
        if (!cancelled) setDown(false);
      } catch {
        failures += 1;
        if (!cancelled && failures >= 2) setDown(true);
      }
    }

    void poll();
    const id = setInterval(poll, 30000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (!down) return null;

  return (
    <div
      role="status"
      className="bg-negative/15 px-4 py-2 text-center text-sm text-text-primary"
    >
      Backend unreachable — showing sample data. Live results will return once
      the service is back (free-tier instances can take up to a minute to wake).
    </div>
  );
}
