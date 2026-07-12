import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { PriceTrendChart } from "@/components/charts/price-trend-chart";
import { DeveloperLeaderboardChart } from "@/components/charts/developer-leaderboard-chart";
import { OffPlanFunnelChart } from "@/components/charts/off-plan-funnel-chart";
import { fetchMarketTrends, fetchDeveloperLeaderboard, fetchOffPlanFunnel } from "@/lib/api";

export default async function MarketAnalyticsPage() {
  const [trends, developers, offPlan] = await Promise.all([
    fetchMarketTrends(),
    fetchDeveloperLeaderboard(),
    fetchOffPlanFunnel(),
  ]);

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <h1 className="font-display text-2xl font-semibold text-text-primary">Analytics</h1>
      <p className="mt-1 text-sm text-text-muted">
        Price trends, developer track record, and off-plan sell-through — aggregated from the
        seeded transaction dataset.
      </p>

      <div className="mt-6 flex flex-col gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Price trend by community</CardTitle>
          </CardHeader>
          <CardContent>
            <PriceTrendChart trends={trends} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Developer track-record leaderboard</CardTitle>
          </CardHeader>
          <CardContent>
            <DeveloperLeaderboardChart developers={developers} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Off-plan percent-sold funnel</CardTitle>
          </CardHeader>
          <CardContent>
            <OffPlanFunnelChart projects={offPlan} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
