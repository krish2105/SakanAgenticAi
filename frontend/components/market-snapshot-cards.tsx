import { Card, CardContent, CardHeader, CardDescription } from "@/components/ui/card";
import { TiltCard } from "@/components/motion/tilt-card";
import { RevealGroup, RevealItem } from "@/components/motion/reveal";
import { AnimatedCounter } from "@/components/motion/animated-counter";

export function MarketSnapshotCards({
  snapshot,
}: {
  snapshot: { community: string; avg_price_per_sqft: number }[];
}) {
  return (
    <RevealGroup className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {snapshot.slice(0, 4).map((s) => (
        <RevealItem key={s.community}>
          <TiltCard>
            <Card className="hover:-translate-y-1">
              <CardHeader className="gap-0.5 pb-2">
                <CardDescription className="truncate">{s.community}</CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="font-mono text-lg font-medium text-text-primary">
                  <AnimatedCounter value={Math.round(s.avg_price_per_sqft)} prefix="AED " />
                </div>
                <div className="font-mono text-[11px] text-text-muted">avg / sqft</div>
              </CardContent>
            </Card>
          </TiltCard>
        </RevealItem>
      ))}
    </RevealGroup>
  );
}
