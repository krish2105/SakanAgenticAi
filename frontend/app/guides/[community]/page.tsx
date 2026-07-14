import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { CompsTable } from "@/components/comps-table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchMarketSnapshot, fetchCommunityTrend, fetchComps } from "@/lib/api";
import { communityToSlug } from "@/lib/community-slug";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://sakan-agentic-ai.vercel.app";

/** Resolves a URL slug back to the real community name by forward-matching
 * against the live list -- see lib/community-slug.ts for why a naive
 * reverse-slugify is unsafe (breaks on acronyms like "DAMAC"). */
async function resolveCommunity(slug: string): Promise<{ community: string; avg_price_per_sqft: number } | null> {
  const snapshot = await fetchMarketSnapshot(20);
  return snapshot.find((row) => communityToSlug(row.community) === slug) || null;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ community: string }>;
}): Promise<Metadata> {
  const { community: slug } = await params;
  const match = await resolveCommunity(slug);
  if (!match) return { title: "Community not found" };

  const price = Math.round(match.avg_price_per_sqft).toLocaleString();
  return {
    title: `${match.community} Property Prices & Market Data`,
    description: `${match.community} real estate: average price of AED ${price} per square foot, recent comparable transactions, and price trends sourced directly from transaction records.`,
    alternates: { canonical: `${SITE_URL}/guides/${slug}` },
  };
}

export default async function CommunityGuidePage({
  params,
}: {
  params: Promise<{ community: string }>;
}) {
  const { community: slug } = await params;
  const match = await resolveCommunity(slug);
  if (!match) notFound();

  const [trend, comps] = await Promise.all([
    fetchCommunityTrend(match.community),
    fetchComps({ community: match.community, limit: 8 }),
  ]);

  const sortedTrend = [...trend].sort((a, b) => a.month.localeCompare(b.month));
  const prices = sortedTrend.map((t) => t.avg_price_per_sqft).filter((p) => p != null);
  const minPrice = prices.length ? Math.min(...prices) : null;
  const maxPrice = prices.length ? Math.max(...prices) : null;
  const latest = sortedTrend[sortedTrend.length - 1];

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Place",
    name: match.community,
    address: { "@type": "PostalAddress", addressLocality: match.community, addressRegion: "Dubai", addressCountry: "AE" },
    additionalProperty: {
      "@type": "PropertyValue",
      name: "Average price per square foot (AED)",
      value: Math.round(match.avg_price_per_sqft),
    },
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      {/* JSON-LD, built from the resolved community match above -- not raw user input. */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <Link href="/guides" className="text-xs text-text-muted hover:text-text-primary">
        &larr; All communities
      </Link>
      <p className="mt-2 font-mono text-xs uppercase tracking-wider text-text-muted">Market guide</p>
      <h1 className="mt-1 font-display text-2xl font-semibold text-text-primary">{match.community}</h1>

      <p className="mt-4 max-w-2xl text-sm text-text-primary">
        The average transaction price in {match.community} is{" "}
        <strong>AED {Math.round(match.avg_price_per_sqft).toLocaleString()} per square foot</strong>
        {minPrice != null && maxPrice != null && minPrice !== maxPrice && (
          <>
            , ranging from AED {Math.round(minPrice).toLocaleString()} to AED{" "}
            {Math.round(maxPrice).toLocaleString()} per sqft across the recorded months
          </>
        )}
        . {latest ? `The most recent month on record (${latest.month}) averaged AED ${Math.round(latest.avg_price_per_sqft).toLocaleString()} per sqft.` : ""}{" "}
        These figures come straight from the comparable transactions below, not a written estimate
        — every number here is traceable to a real recorded sale.
      </p>

      {sortedTrend.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Monthly average price / sqft</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Monthly price trend table">
              <table className="w-full min-w-[360px] text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase text-text-muted">
                    <th className="py-1.5 font-medium">Month</th>
                    <th className="py-1.5 font-medium">Avg AED/sqft</th>
                  </tr>
                </thead>
                <tbody className="font-mono text-xs">
                  {sortedTrend.map((point) => (
                    <tr key={point.month} className="border-b border-border last:border-0">
                      <td className="py-1.5">{point.month}</td>
                      <td className="py-1.5 text-text-primary">
                        {point.avg_price_per_sqft != null ? Math.round(point.avg_price_per_sqft).toLocaleString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="mt-6">
        <CompsTable comps={comps} />
      </div>

      <p className="mt-6 text-xs text-text-muted">
        Want a defensible valuation for a specific unit in {match.community}, with a RERA
        compliance check?{" "}
        <Link href="/" className="text-brass underline">
          Ask Sakan AI
        </Link>
        .
      </p>
    </div>
  );
}
