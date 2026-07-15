import type { Metadata } from "next";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { PriceTrendChart } from "@/components/charts/price-trend-chart";
import { DeveloperLeaderboardChart } from "@/components/charts/developer-leaderboard-chart";
import { OffPlanFunnelChart } from "@/components/charts/off-plan-funnel-chart";
import { T } from "@/components/t";
import { fetchMarketTrends, fetchDeveloperLeaderboard, fetchOffPlanFunnel } from "@/lib/api";
import { Reveal, RevealGroup, RevealItem } from "@/components/motion/reveal";

export const metadata: Metadata = {
  title: "Analytics",
  description: "Dubai real estate price trends, developer track record, and off-plan sell-through.",
};

export default async function MarketAnalyticsPage() {
  const [trends, developers, offPlan] = await Promise.all([
    fetchMarketTrends(),
    fetchDeveloperLeaderboard(),
    fetchOffPlanFunnel(),
  ]);

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <Reveal>
        <h1 className="font-display text-2xl font-semibold text-text-primary">
          <T k="market.title" />
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          <T k="market.subtitle" />
        </p>
      </Reveal>

      <RevealGroup className="mt-6 flex flex-col gap-4">
        <RevealItem>
          <Card className="hover:-translate-y-0">
            <CardHeader>
              <CardTitle>Price trend by community</CardTitle>
            </CardHeader>
            <CardContent>
              <PriceTrendChart trends={trends} />
            </CardContent>
          </Card>
        </RevealItem>

        <RevealItem>
          <Card className="hover:-translate-y-0">
            <CardHeader>
              <CardTitle>Developer track-record leaderboard</CardTitle>
            </CardHeader>
            <CardContent>
              <DeveloperLeaderboardChart developers={developers} />
            </CardContent>
          </Card>
        </RevealItem>

        <RevealItem>
          <Card className="hover:-translate-y-0">
            <CardHeader>
              <CardTitle>Off-plan percent-sold funnel</CardTitle>
            </CardHeader>
            <CardContent>
              <OffPlanFunnelChart projects={offPlan} />
            </CardContent>
          </Card>
        </RevealItem>
      </RevealGroup>
    </div>
  );
}
