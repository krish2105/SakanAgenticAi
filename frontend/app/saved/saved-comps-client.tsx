"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bookmark, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ProvenanceBadge } from "@/components/comps-table";
import { WatchlistStats } from "@/components/watchlist-stats";
import { SavedSearchesPanel } from "@/components/saved-searches-panel";
import { useAuth } from "@/components/auth-provider";
import { fetchSavedComps, unsaveComp, AuthRequiredError } from "@/lib/api";
import type { Comp } from "@/lib/types";

export function SavedCompsClient() {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const [comps, setComps] = useState<Comp[] | null>(null);
  const [error, setError] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    setComps(null);
    fetchSavedComps(token)
      .then((rows) => {
        setError(false);
        setComps(rows);
      })
      .catch((err) => {
        if (err instanceof AuthRequiredError) {
          router.push("/login?next=/saved");
          return;
        }
        setError(true);
        setComps([]);
      });
  }, [token, router]);

  useEffect(() => {
    if (authLoading) return;
    if (!token) {
      router.push("/login?next=/saved");
      return;
    }
    let cancelled = false;
    fetchSavedComps(token)
      .then((rows) => {
        if (cancelled) return;
        setError(false);
        setComps(rows);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof AuthRequiredError) {
          router.push("/login?next=/saved");
          return;
        }
        setError(true);
        setComps([]);
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, token, router]);

  function handleRemove(transactionId: string) {
    if (!token) return;
    setRemovingId(transactionId);
    unsaveComp(transactionId, token)
      .then(() => {
        setComps((prev) => (prev ? prev.filter((c) => c.transaction_id !== transactionId) : prev));
      })
      .catch(() => {
        // Leave the item in place -- the Remove button is still there to retry.
      })
      .finally(() => setRemovingId(null));
  }

  const isLoading = authLoading || comps === null;

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-text-muted">Watchlist</p>
          <h1 className="mt-1 font-display text-2xl font-semibold text-text-primary">Saved comps</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={isLoading}>
            <RefreshCw size={14} />
            Refresh
          </Button>
          <Link href="/comps">
            <Button size="sm">Browse comps</Button>
          </Link>
        </div>
      </div>

      {!isLoading && <div className="mt-6"><SavedSearchesPanel /></div>}

      {!isLoading && comps && <div><WatchlistStats comps={comps} /></div>}

      <div className={comps && comps.length > 0 ? "flex flex-col gap-3" : "mt-6 flex flex-col gap-3"}>
        {isLoading &&
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border bg-surface p-4">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="mt-3 h-3 w-1/3" />
            </div>
          ))}

        {!isLoading && error && comps?.length === 0 && (
          <div className="rounded-xl border border-negative/40 bg-surface p-6 text-center">
            <p className="text-sm text-text-primary">Couldn&apos;t load your watchlist.</p>
            <p className="mt-1 text-sm text-text-muted">
              The backend may be waking up (free tier). Try again in a moment.
            </p>
            <Button className="mt-4" size="sm" onClick={() => void load()}>
              Retry
            </Button>
          </div>
        )}

        {!isLoading && !error && comps && comps.length === 0 && (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <Bookmark size={20} className="mx-auto text-text-muted" />
            <p className="mt-3 text-sm text-text-primary">Nothing saved yet.</p>
            <p className="mt-1 text-sm text-text-muted">
              Tap the bookmark icon on any comp in the Comps Explorer to add it here.
            </p>
            <Link href="/comps">
              <Button className="mt-4" size="sm">
                Browse comps
              </Button>
            </Link>
          </div>
        )}

        {!isLoading &&
          comps &&
          comps.length > 0 &&
          comps.map((c) => (
            <div
              key={c.transaction_id}
              className="rounded-xl border border-border bg-surface p-4 transition-colors hover:border-brass/50"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-medium text-text-primary">{c.building}</p>
                  <p className="mt-1 font-mono text-xs text-text-muted">
                    {c.community} · {c.bedrooms} bed · AED {c.price?.toLocaleString()}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <ProvenanceBadge provenance={c.data_provenance} />
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={removingId === c.transaction_id}
                    onClick={() => handleRemove(c.transaction_id)}
                  >
                    Remove
                  </Button>
                </div>
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}
