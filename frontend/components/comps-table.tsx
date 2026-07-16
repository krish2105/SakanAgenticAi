"use client";

import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SaveCompButton } from "@/components/save-comp-button";
import { T } from "@/components/t";
import { useAuth } from "@/components/auth-provider";
import { capture } from "@/lib/analytics";
import { downloadCompsCsv } from "@/lib/csv-export";
import { fetchSavedComps, saveComp, unsaveComp } from "@/lib/api";
import type { Comp } from "@/lib/types";

/** Phase 7: every comp always shows whether it's demo/synthetic data, the
 * real public DLD/Kaggle open dataset, or (once one exists) a licensed
 * partner feed -- so "is this a real number?" never has to be taken on
 * faith. Unknown/missing provenance renders nothing rather than guessing. */
export function ProvenanceBadge({ provenance }: { provenance?: string }) {
  if (provenance === "licensed_partner") {
    return (
      <Badge variant="positive">
        <T k="comps.provenanceLicensedPartner" />
      </Badge>
    );
  }
  if (provenance === "dld_open_free") {
    return (
      <Badge variant="positive">
        <T k="comps.provenanceDldOpenFree" />
      </Badge>
    );
  }
  if (provenance === "dld_kaggle") {
    return (
      <Badge variant="default">
        <T k="comps.provenanceDldKaggle" />
      </Badge>
    );
  }
  if (provenance === "dld_bayut") {
    return (
      <Badge variant="default">
        <T k="comps.provenanceDldBayut" />
      </Badge>
    );
  }
  if (provenance === "synthetic") {
    return (
      <Badge variant="muted">
        <T k="comps.provenanceSynthetic" />
      </Badge>
    );
  }
  return null;
}

export function CompsTable({ comps }: { comps: Comp[] }) {
  const { token } = useAuth();
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());

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
          // Watchlist overlay is best-effort -- a failed fetch just means
          // every bookmark renders unsaved, not a broken table.
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
      setSavedIds((prev) => {
        const next = new Set(prev);
        if (wasSaved) next.add(transactionId);
        else next.delete(transactionId);
        return next;
      });
    });
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
        <CardTitle>
          <T k="comps.comparableTransactions" />
        </CardTitle>
        {comps.length > 0 && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              capture("comps_csv_exported", { count: comps.length });
              downloadCompsCsv(comps);
            }}
          >
            <Download size={14} />
            Export CSV
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {comps.length === 0 ? (
          <p className="text-sm text-text-muted">
            <T k="comps.noComps" />
          </p>
        ) : (
          <>
            {/* Below sm: this table has 7 columns -- a horizontal-scroll
                table hides most of them off-screen with no visible
                affordance. A stacked card per comp keeps every field
                on-screen instead. */}
            <ul className="flex flex-col gap-2 sm:hidden">
              {comps.map((c) => (
                <li key={c.transaction_id} className="rounded-lg border border-border p-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="min-w-0 truncate font-body text-sm font-medium text-text-primary">{c.building}</p>
                    <div className="flex shrink-0 items-center gap-1">
                      <ProvenanceBadge provenance={c.data_provenance} />
                      {token && (
                        <SaveCompButton saved={savedIds.has(c.transaction_id)} onToggle={() => toggleSaved(c.transaction_id)} />
                      )}
                    </div>
                  </div>
                  <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 font-mono text-xs">
                    <span className="text-brass">{c.transaction_id}</span>
                    <span className="text-text-muted text-right">{c.date}</span>
                    <span className="text-text-muted">{c.bedrooms} bed</span>
                    <span className="text-text-primary text-right">AED {c.price?.toLocaleString()}</span>
                    <span className="text-text-muted col-span-2 text-right">
                      {c.price_per_sqft?.toLocaleString()} AED/sqft
                    </span>
                  </div>
                </li>
              ))}
            </ul>

          <div className="hidden overflow-x-auto sm:block" tabIndex={0} role="region" aria-label="Comparable transactions table">
            <table className="w-full min-w-[560px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-text-muted">
                  <th className="py-2 pr-3 font-medium">
                    <T k="comps.colTransaction" />
                  </th>
                  <th className="py-2 pr-3 font-medium">
                    <T k="comps.colBuilding" />
                  </th>
                  <th className="py-2 pr-3 font-medium">
                    <T k="comps.colBeds" />
                  </th>
                  <th className="py-2 pr-3 font-medium">
                    <T k="comps.colPrice" />
                  </th>
                  <th className="py-2 pr-3 font-medium">
                    <T k="comps.colPricePerSqft" />
                  </th>
                  <th className="py-2 pr-3 font-medium">
                    <T k="comps.colDate" />
                  </th>
                  <th className="py-2 font-medium">
                    <T k="comps.colSource" />
                  </th>
                  {token && <th className="py-2 font-medium" aria-label="Watchlist" />}
                </tr>
              </thead>
              <tbody className="font-mono text-xs">
                {comps.map((c) => (
                  <tr key={c.transaction_id} className="border-b border-border last:border-0">
                    <td className="py-2 pr-3 text-brass">{c.transaction_id}</td>
                    <td className="py-2 pr-3 font-body text-text-primary">{c.building}</td>
                    <td className="py-2 pr-3">{c.bedrooms}</td>
                    <td className="py-2 pr-3 text-text-primary">AED {c.price?.toLocaleString()}</td>
                    <td className="py-2 pr-3 text-text-muted">{c.price_per_sqft?.toLocaleString()}</td>
                    <td className="py-2 pr-3 text-text-muted">{c.date}</td>
                    <td className="py-2">
                      <ProvenanceBadge provenance={c.data_provenance} />
                    </td>
                    {token && (
                      <td className="py-2">
                        <SaveCompButton saved={savedIds.has(c.transaction_id)} onToggle={() => toggleSaved(c.transaction_id)} />
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
