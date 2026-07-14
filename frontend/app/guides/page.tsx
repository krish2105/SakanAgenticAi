import type { Metadata } from "next";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { fetchMarketSnapshot } from "@/lib/api";
import { communityToSlug } from "@/lib/community-slug";

export const metadata: Metadata = {
  title: "Dubai Real Estate Market Guides",
  description:
    "Community-by-community price data for Dubai real estate: average price per square foot, recent comparable sales, and market trends, sourced directly from transaction records.",
};

export default async function GuidesPage() {
  const snapshot = await fetchMarketSnapshot(20);
  const sorted = [...snapshot].sort((a, b) => a.community.localeCompare(b.community));

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <p className="font-mono text-xs uppercase tracking-wider text-text-muted">Market guides</p>
      <h1 className="mt-1 font-display text-2xl font-semibold text-text-primary">
        Dubai real estate, community by community
      </h1>
      <p className="mt-2 max-w-2xl text-sm text-text-muted">
        Average price per square foot and comparable sales for {sorted.length}{" "}
        Dubai communities, computed directly from transaction records rather than written up by
        hand — the same data Sakan AI&apos;s agents use to answer a deal query.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {sorted.map((row) => (
          <Link key={row.community} href={`/guides/${communityToSlug(row.community)}`}>
            <Card className="transition-colors hover:border-brass/50">
              <CardContent className="flex items-center justify-between p-4">
                <span className="font-medium text-text-primary">{row.community}</span>
                <span className="font-mono text-sm text-brass">
                  AED {Math.round(row.avg_price_per_sqft).toLocaleString()}/sqft
                </span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
