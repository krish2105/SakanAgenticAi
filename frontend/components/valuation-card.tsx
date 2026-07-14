import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CitedText } from "@/components/cited-text";
import { ValuationRangeChart } from "@/components/charts/valuation-range-chart";
import { DealScoreGauge } from "@/components/deal-score-gauge";
import { T } from "@/components/t";
import { computeDealScore } from "@/lib/deal-score";
import type { Comp } from "@/lib/types";

export function ValuationCard({
  low,
  high,
  method,
  rationale,
  comps = [],
}: {
  low?: number | null;
  high?: number | null;
  method?: string | null;
  rationale?: string | null;
  comps?: Comp[];
}) {
  const score = low != null && high != null ? computeDealScore(low, high, comps) : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <T k="valuation.title" />
        </CardTitle>
      </CardHeader>
      <CardContent>
        {low != null && high != null ? (
          <>
            <div className="font-mono text-2xl font-medium text-text-primary">
              AED {Math.round(low).toLocaleString()} – {Math.round(high).toLocaleString()}
            </div>
            {method && (
              <p className="mt-2 text-sm text-text-muted">
                <T k="valuation.method" />: {method}
              </p>
            )}
            {rationale && (
              <p className="mt-2 text-sm text-text-muted">
                <CitedText text={rationale} />
              </p>
            )}

            {comps.length >= 2 && (
              <div className="mt-5 border-t border-border pt-4">
                <ValuationRangeChart low={low} high={high} comps={comps} />
              </div>
            )}
            {score && (
              <div className="mt-4 border-t border-border pt-4">
                <DealScoreGauge score={score} />
              </div>
            )}
          </>
        ) : (
          <p className="text-sm text-text-muted">
            <T k="valuation.notYetComputed" />
          </p>
        )}
      </CardContent>
    </Card>
  );
}
