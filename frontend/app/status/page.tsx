import type { Metadata } from "next";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { fetchReadiness } from "@/lib/api";

export const metadata: Metadata = {
  title: "System Status",
  description: "Live status of Sakan AI's backend, database, cache, and vector search.",
};

const CHECK_LABELS: Record<string, string> = {
  database: "Database",
  redis: "Cache (Redis)",
  qdrant: "Vector search (Qdrant)",
};

// This page fetches /readyz on every request (no caching) so it always
// reflects the backend's actual current state, not a stale build-time snapshot.
export const dynamic = "force-dynamic";

export default async function StatusPage() {
  const report = await fetchReadiness();

  const overall = !report.reachable
    ? { label: "Unreachable", variant: "negative" as const }
    : report.ready
      ? { label: "Operational", variant: "positive" as const }
      : { label: "Degraded", variant: "negative" as const };

  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">Status</p>
      <h1 className="mt-1 font-display text-3xl font-semibold text-text-primary">System status</h1>
      <p className="mt-2 text-sm text-text-muted">
        Live, not cached — this page calls the backend&apos;s own readiness check on every load.
      </p>

      <Card className="mt-6">
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Overall</CardTitle>
          <Badge variant={overall.variant}>{overall.label}</Badge>
        </CardHeader>
        {!report.reachable && (
          <CardContent>
            <p className="text-sm text-text-muted">
              The backend didn&apos;t respond. On the free tier this can mean a cold start (up to
              ~60s after 15 minutes idle) rather than a real outage — try reloading in a moment.
            </p>
          </CardContent>
        )}
      </Card>

      {report.reachable && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle>Components</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {Object.entries(report.checks).map(([key, check]) => (
              <div key={key} className="flex items-center justify-between gap-4 border-b border-border pb-3 last:border-0 last:pb-0">
                <div className="min-w-0">
                  <p className="text-sm text-text-primary">{CHECK_LABELS[key] || key}</p>
                  <p className="mt-0.5 truncate text-xs text-text-muted">{check.detail}</p>
                </div>
                <Badge variant={check.ok ? "positive" : "negative"}>{check.ok ? "OK" : "Error"}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <p className="mt-6 text-xs text-text-muted">
        Only the database gates overall readiness — a degraded cache or vector search falls back to
        documented behavior (in-memory pub/sub, or an honest &quot;unable to verify&quot; compliance
        response) rather than taking the whole app down.
      </p>
    </div>
  );
}
