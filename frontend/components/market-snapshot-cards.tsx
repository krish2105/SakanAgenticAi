import { Card, CardContent, CardHeader, CardDescription } from "@/components/ui/card";

export function MarketSnapshotCards({
  snapshot,
}: {
  snapshot: { community: string; avg_price_per_sqft: number }[];
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {snapshot.slice(0, 4).map((s) => (
        <Card key={s.community}>
          <CardHeader className="gap-0.5 pb-2">
            <CardDescription className="truncate">{s.community}</CardDescription>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="font-mono text-lg font-medium text-text-primary">
              AED {Math.round(s.avg_price_per_sqft).toLocaleString()}
            </div>
            <div className="font-mono text-[11px] text-text-muted">avg / sqft</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
