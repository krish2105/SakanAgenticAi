"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Download, BarChart3, BellPlus } from "lucide-react";
import { CompsFilterBar, type CompsFilters } from "@/components/comps-filter-bar";
import { ProvenanceBadge } from "@/components/comps-table";
import { PriceDistributionChart } from "@/components/charts/price-distribution-chart";
import { Button } from "@/components/ui/button";
import { SaveCompButton } from "@/components/save-comp-button";
import { T } from "@/components/t";
import { useAuth } from "@/components/auth-provider";
import { useLocale } from "@/components/locale-provider";
import { useToast } from "@/components/ui/toast";
import { fetchComps, fetchSavedComps, saveComp, unsaveComp, createSavedSearch } from "@/lib/api";
import { capture } from "@/lib/analytics";
import { downloadCompsCsv } from "@/lib/csv-export";
import { cn } from "@/lib/utils";
import type { Comp } from "@/lib/types";

const CompsMap = dynamic(() => import("@/components/comps-map").then((m) => m.CompsMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center text-sm text-text-muted">
      Loading map…
    </div>
  ),
});

export function CompsExplorerClient({ initialComps }: { initialComps: Comp[] }) {
  const { t } = useLocale();
  const { token } = useAuth();
  const { toast } = useToast();
  const [filters, setFilters] = useState<CompsFilters>({ community: "", type: "", bedrooms: "" });
  const [comps, setComps] = useState<Comp[]>(initialComps);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [showDistribution, setShowDistribution] = useState(false);
  const [savingSearch, setSavingSearch] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadComps() {
      setLoading(true);
      try {
        const data = await fetchComps({
          community: filters.community || undefined,
          type: filters.type || undefined,
          bedrooms: filters.bedrooms || undefined,
          limit: 100,
        });
        if (!cancelled) setComps(data);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadComps();
    return () => {
      cancelled = true;
    };
  }, [filters]);

  useEffect(() => {
    let cancelled = false;

    function syncSaved() {
      if (!token) {
        setSavedIds(new Set());
        return;
      }
      fetchSavedComps(token)
        .then((saved) => {
          if (!cancelled) setSavedIds(new Set(saved.map((c) => c.transaction_id)));
        })
        .catch(() => {
          // Watchlist state is a nice-to-have overlay -- a failed fetch just
          // means every bookmark renders unsaved, not a broken page.
        });
    }

    syncSaved();
    return () => {
      cancelled = true;
    };
  }, [token]);

  function toggleSaved(transactionId: string) {
    if (!token) return;
    const wasSaved = savedIds.has(transactionId);
    setSavedIds((prev) => {
      const next = new Set(prev);
      if (wasSaved) next.delete(transactionId);
      else next.add(transactionId);
      return next;
    });
    capture(wasSaved ? "comp_unsaved" : "comp_saved", { transaction_id: transactionId });
    const request = wasSaved ? unsaveComp(transactionId, token) : saveComp(transactionId, token);
    request.catch(() => {
      // Revert the optimistic update on failure.
      setSavedIds((prev) => {
        const next = new Set(prev);
        if (wasSaved) next.add(transactionId);
        else next.delete(transactionId);
        return next;
      });
    });
  }

  async function handleSaveSearch() {
    if (!token) return;
    setSavingSearch(true);
    try {
      await createSavedSearch(
        {
          community: filters.community || undefined,
          property_type: filters.type || undefined,
          bedrooms: filters.bedrooms ? Number(filters.bedrooms) : undefined,
        },
        token
      );
      capture("search_saved", { ...filters });
      toast("Search saved — you'll get an email digest of matches.", "success");
    } catch {
      toast("Couldn't save this search. Try again.", "error");
    } finally {
      setSavingSearch(false);
    }
  }

  return (
    <div className="flex h-full flex-col gap-4 px-6 py-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-text-primary">{t("comps.title")}</h1>
          <p className="text-sm text-text-muted">
            {loading ? "Loading…" : `${comps.length} transactions`}
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <CompsFilterBar filters={filters} onChange={setFilters} />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowDistribution((v) => !v)}
            aria-pressed={showDistribution}
          >
            <BarChart3 size={14} />
            {showDistribution ? "Hide distribution" : "Show distribution"}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={comps.length === 0}
            onClick={() => {
              capture("comps_csv_exported", { count: comps.length });
              downloadCompsCsv(comps);
            }}
          >
            <Download size={14} />
            Export CSV
          </Button>
          {token && (
            <Button type="button" variant="outline" size="sm" disabled={savingSearch} onClick={handleSaveSearch}>
              <BellPlus size={14} />
              {savingSearch ? "Saving…" : "Save search"}
            </Button>
          )}
        </div>
      </div>

      {showDistribution && (
        <div className="rounded-xl border border-border bg-surface p-4">
          <PriceDistributionChart comps={comps} />
        </div>
      )}

      <div className="grid min-h-0 grid-cols-1 gap-4 lg:h-[calc(100vh-13rem)] lg:grid-cols-2">
        <div className="h-[420px] min-h-0 overflow-hidden rounded-xl border border-border lg:h-full">
          <CompsMap comps={comps} selectedId={selectedId} onSelect={setSelectedId} />
        </div>

        <div
          className="h-[420px] min-h-0 overflow-auto rounded-xl border border-border bg-surface lg:h-full"
          tabIndex={0}
          role="region"
          aria-label="Comparable sales table"
        >
          {/* Below sm: a wide table just hides Beds/Price/Source off-screen
              with no visible scroll affordance -- a stacked card per comp
              keeps every field on-screen without horizontal scrolling. */}
          <ul className="flex flex-col gap-2 p-2 sm:hidden">
            {comps.map((c) => (
              <li
                key={c.transaction_id}
                onClick={() => setSelectedId(c.transaction_id)}
                className={cn(
                  "cursor-pointer rounded-lg border border-border p-3 transition-colors",
                  selectedId === c.transaction_id ? "bg-brass/10 border-brass/40" : "hover:bg-border/30"
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-body text-sm font-medium text-text-primary">{c.building}</p>
                    <p className="truncate text-xs text-text-muted">{c.community}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <ProvenanceBadge provenance={c.data_provenance} />
                    {token && (
                      <SaveCompButton
                        saved={savedIds.has(c.transaction_id)}
                        onToggle={() => toggleSaved(c.transaction_id)}
                      />
                    )}
                  </div>
                </div>
                <div className="mt-2 flex items-center justify-between font-mono text-xs">
                  <span className="text-brass">{c.transaction_id}</span>
                  <span className="text-text-muted">{c.bedrooms} bed</span>
                  <span className="text-text-primary">AED {c.price?.toLocaleString()}</span>
                </div>
              </li>
            ))}
          </ul>

          <table className="hidden w-full min-w-[520px] border-collapse text-sm sm:table">
            <thead className="sticky top-0 bg-surface">
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-text-muted">
                <th className="px-3 py-2 font-medium">Transaction</th>
                <th className="px-3 py-2 font-medium">Building</th>
                <th className="px-3 py-2 font-medium">Community</th>
                <th className="px-3 py-2 font-medium">Beds</th>
                <th className="px-3 py-2 font-medium">Price</th>
                <th className="px-3 py-2 font-medium">
                  <T k="comps.colSource" />
                </th>
                {token && <th className="px-3 py-2 font-medium" aria-label="Watchlist" />}
              </tr>
            </thead>
            <tbody className="font-mono text-xs">
              {comps.map((c) => (
                <tr
                  key={c.transaction_id}
                  onClick={() => setSelectedId(c.transaction_id)}
                  className={cn(
                    "cursor-pointer border-b border-border last:border-0 hover:bg-border/30",
                    selectedId === c.transaction_id && "bg-brass/10"
                  )}
                >
                  <td className="px-3 py-2 text-brass">{c.transaction_id}</td>
                  <td className="px-3 py-2 font-body text-text-primary">{c.building}</td>
                  <td className="px-3 py-2 font-body text-text-muted">{c.community}</td>
                  <td className="px-3 py-2">{c.bedrooms}</td>
                  <td className="px-3 py-2 text-text-primary">AED {c.price?.toLocaleString()}</td>
                  <td className="px-3 py-2">
                    <ProvenanceBadge provenance={c.data_provenance} />
                  </td>
                  {token && (
                    <td className="px-3 py-2">
                      <SaveCompButton
                        saved={savedIds.has(c.transaction_id)}
                        onToggle={() => toggleSaved(c.transaction_id)}
                      />
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
