"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/components/auth-provider";
import { fetchDeals, AuthRequiredError } from "@/lib/api";
import type { DealStatus, DealSummary } from "@/lib/types";

const STATUS_META: Record<DealStatus, { label: string; variant: "positive" | "muted" | "negative" }> = {
  complete: { label: "Complete", variant: "positive" },
  processing: { label: "Processing", variant: "muted" },
  error: { label: "Error", variant: "negative" },
};

function formatDate(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}

export function DealsHistoryClient() {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const [deals, setDeals] = useState<DealSummary[] | null>(null);
  const [error, setError] = useState(false);

  // For the Refresh/Retry buttons (event handlers, so setState here is fine).
  const load = useCallback(() => {
    if (!token) return;
    setDeals(null); // back to the skeleton state while refetching
    fetchDeals(token)
      .then((rows) => {
        setError(false);
        setDeals(rows);
      })
      .catch((err) => {
        if (err instanceof AuthRequiredError) {
          router.push("/login?next=/deals");
          return;
        }
        setError(true);
        setDeals([]);
      });
  }, [token, router]);

  // Initial load on mount. setState lives inside the async callbacks (not a
  // synchronous call in the effect body) to avoid cascading renders.
  useEffect(() => {
    if (authLoading) return;
    if (!token) {
      router.push("/login?next=/deals");
      return;
    }
    let cancelled = false;
    fetchDeals(token)
      .then((rows) => {
        if (cancelled) return;
        setError(false);
        setDeals(rows);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof AuthRequiredError) {
          router.push("/login?next=/deals");
          return;
        }
        setError(true);
        setDeals([]);
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, token, router]);

  const isLoading = authLoading || deals === null;

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-text-muted">History</p>
          <h1 className="mt-1 font-display text-2xl font-semibold text-text-primary">My deals</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={isLoading}>
            <RefreshCw size={14} />
            Refresh
          </Button>
          <Link href="/">
            <Button size="sm">New query</Button>
          </Link>
        </div>
      </div>

      <div className="mt-6 flex flex-col gap-3">
        {isLoading &&
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border bg-surface p-4">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="mt-3 h-3 w-1/3" />
            </div>
          ))}

        {!isLoading && error && (
          <div className="rounded-xl border border-negative/40 bg-surface p-6 text-center">
            <p className="text-sm text-text-primary">Couldn&apos;t load your deals.</p>
            <p className="mt-1 text-sm text-text-muted">
              The backend may be waking up (free tier). Try again in a moment.
            </p>
            <Button className="mt-4" size="sm" onClick={() => void load()}>
              Retry
            </Button>
          </div>
        )}

        {!isLoading && !error && deals && deals.length === 0 && (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <p className="text-sm text-text-primary">No deals yet.</p>
            <p className="mt-1 text-sm text-text-muted">
              Ask Sakan a deal question and it&apos;ll show up here.
            </p>
            <Link href="/">
              <Button className="mt-4" size="sm">
                Ask your first question
              </Button>
            </Link>
          </div>
        )}

        {!isLoading &&
          !error &&
          deals?.map((deal) => {
            const meta = STATUS_META[deal.status] ?? STATUS_META.processing;
            return (
              <Link
                key={deal.query_id}
                href={`/deals/${deal.query_id}`}
                className="group rounded-xl border border-border bg-surface p-4 transition-colors hover:border-brass/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brass"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-text-primary group-hover:text-brass">
                      {deal.raw_query}
                    </p>
                    <p className="mt-1 font-mono text-xs text-text-muted">
                      Deal #{deal.query_id}
                      {deal.created_at ? ` · ${formatDate(deal.created_at)}` : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge variant={meta.variant}>{meta.label}</Badge>
                    <FileText size={16} className="text-text-muted" aria-hidden="true" />
                  </div>
                </div>
              </Link>
            );
          })}
      </div>
    </div>
  );
}
