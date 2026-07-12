import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { Comp } from "@/lib/types";

export function CompsTable({ comps }: { comps: Comp[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Comparable Transactions</CardTitle>
      </CardHeader>
      <CardContent>
        {comps.length === 0 ? (
          <p className="text-sm text-text-muted">No comparable transactions retrieved yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-text-muted">
                  <th className="py-2 pr-3 font-medium">Transaction</th>
                  <th className="py-2 pr-3 font-medium">Building</th>
                  <th className="py-2 pr-3 font-medium">Beds</th>
                  <th className="py-2 pr-3 font-medium">Price</th>
                  <th className="py-2 pr-3 font-medium">AED/sqft</th>
                  <th className="py-2 font-medium">Date</th>
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
                    <td className="py-2 text-text-muted">{c.date}</td>
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
