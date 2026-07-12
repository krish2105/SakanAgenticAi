import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CitedText } from "@/components/cited-text";

export function ValuationCard({
  low,
  high,
  method,
  rationale,
}: {
  low?: number | null;
  high?: number | null;
  method?: string | null;
  rationale?: string | null;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Valuation Range</CardTitle>
      </CardHeader>
      <CardContent>
        {low != null && high != null ? (
          <>
            <div className="font-mono text-2xl font-medium text-text-primary">
              AED {Math.round(low).toLocaleString()} – {Math.round(high).toLocaleString()}
            </div>
            {method && <p className="mt-2 text-sm text-text-muted">Method: {method}</p>}
            {rationale && (
              <p className="mt-2 text-sm text-text-muted">
                <CitedText text={rationale} />
              </p>
            )}
          </>
        ) : (
          <p className="text-sm text-text-muted">Not yet computed.</p>
        )}
      </CardContent>
    </Card>
  );
}
