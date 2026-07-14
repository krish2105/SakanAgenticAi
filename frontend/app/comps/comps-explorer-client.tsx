"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Download } from "lucide-react";
import { CompsFilterBar, type CompsFilters } from "@/components/comps-filter-bar";
import { ProvenanceBadge } from "@/components/comps-table";
import { Button } from "@/components/ui/button";
import { T } from "@/components/t";
import { useLocale } from "@/components/locale-provider";
import { fetchComps } from "@/lib/api";
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
  const [filters, setFilters] = useState<CompsFilters>({ community: "", type: "", bedrooms: "" });
  const [comps, setComps] = useState<Comp[]>(initialComps);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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
            disabled={comps.length === 0}
            onClick={() => {
              capture("comps_csv_exported", { count: comps.length });
              downloadCompsCsv(comps);
            }}
          >
            <Download size={14} />
            Export CSV
          </Button>
        </div>
      </div>

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
                  <ProvenanceBadge provenance={c.data_provenance} />
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
