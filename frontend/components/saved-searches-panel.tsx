"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BellRing } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";
import { fetchSavedSearches, deleteSavedSearch, type SavedSearch } from "@/lib/api";

function describeSearch(s: SavedSearch): string {
  const parts = [s.property_type, s.bedrooms != null ? `${s.bedrooms}BR` : null, s.community].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : "All comps";
}

/** Lists the current user's saved-search email digests (Phase 25). A
 * digest, not a "new listing" alert -- see backend/app/models.py's
 * SavedSearch docstring for why. Removal is the only mutation here; new
 * searches are created from the Comps Explorer's "Save search" button. */
export function SavedSearchesPanel() {
  const { token } = useAuth();
  const [searches, setSearches] = useState<SavedSearch[] | null>(null);
  const [removingId, setRemovingId] = useState<number | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchSavedSearches(token)
      .then((rows) => {
        if (!cancelled) setSearches(rows);
      })
      .catch(() => {
        if (!cancelled) setSearches(null);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  function handleRemove(id: number) {
    if (!token) return;
    setRemovingId(id);
    deleteSavedSearch(id, token)
      .then(() => setSearches((prev) => (prev ? prev.filter((s) => s.id !== id) : prev)))
      .catch(() => {
        // Leave it in place -- the Remove button is still there to retry.
      })
      .finally(() => setRemovingId(null));
  }

  if (!searches || searches.length === 0) return null;

  return (
    <div className="mb-6 rounded-xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="flex items-center gap-1.5 text-xs text-text-muted">
          <BellRing size={13} />
          Saved searches — you&apos;ll get an email digest of matches
        </p>
        <Link href="/comps" className="text-xs text-brass underline decoration-dotted">
          Save another
        </Link>
      </div>
      <div className="mt-3 flex flex-col gap-2">
        {searches.map((s) => (
          <div key={s.id} className="flex items-center justify-between gap-3 rounded-lg border border-border p-2.5">
            <p className="min-w-0 truncate text-sm text-text-primary">{describeSearch(s)}</p>
            <Button variant="ghost" size="sm" disabled={removingId === s.id} onClick={() => handleRemove(s.id)}>
              Remove
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
