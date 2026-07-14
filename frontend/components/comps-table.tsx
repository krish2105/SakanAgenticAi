import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { T } from "@/components/t";
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
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <T k="comps.comparableTransactions" />
        </CardTitle>
      </CardHeader>
      <CardContent>
        {comps.length === 0 ? (
          <p className="text-sm text-text-muted">
            <T k="comps.noComps" />
          </p>
        ) : (
          <div className="overflow-x-auto">
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
