import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { CompsTable } from "@/components/comps-table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchPropertyTypeSnapshot, fetchComps, type PropertyTypeSnapshot } from "@/lib/api";
import { propertyTypeToSlug } from "@/lib/property-type-slug";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://sakan-agentic-ai.vercel.app";

/** Forward-match only -- see lib/property-type-slug.ts / lib/community-slug.ts
 * for why resolution goes slug -> live list, never list -> slug -> list. */
async function resolvePropertyType(slug: string): Promise<PropertyTypeSnapshot | null> {
  const snapshot = await fetchPropertyTypeSnapshot();
  return snapshot.find((row) => propertyTypeToSlug(row.property_type) === slug) || null;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ propertyType: string }>;
}): Promise<Metadata> {
  const { propertyType: slug } = await params;
  const match = await resolvePropertyType(slug);
  if (!match) return { title: "Property type not found" };

  const price = Math.round(match.avg_price_per_sqft).toLocaleString();
  return {
    title: `${match.property_type} Prices in Dubai`,
    description: `${match.property_type} real estate in Dubai: average price of AED ${price} per square foot across ${match.transaction_count.toLocaleString()} recorded transactions.`,
    alternates: { canonical: `${SITE_URL}/guides/type/${slug}` },
  };
}

export default async function PropertyTypeGuidePage({
  params,
}: {
  params: Promise<{ propertyType: string }>;
}) {
  const { propertyType: slug } = await params;
  const match = await resolvePropertyType(slug);
  if (!match) notFound();

  const comps = await fetchComps({ type: match.property_type, limit: 8 });

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: `${match.property_type} — Dubai`,
    additionalProperty: {
      "@type": "PropertyValue",
      name: "Average price per square foot (AED)",
      value: Math.round(match.avg_price_per_sqft),
    },
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      {/* JSON-LD, built from the resolved match above -- not raw user input. */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <Link href="/guides" className="text-xs text-text-muted hover:text-text-primary">
        &larr; All guides
      </Link>
      <p className="mt-2 font-mono text-xs uppercase tracking-wider text-text-muted">Property type</p>
      <h1 className="mt-1 font-display text-2xl font-semibold text-text-primary">
        {match.property_type} in Dubai
      </h1>

      <p className="mt-4 max-w-2xl text-sm text-text-primary">
        The average recorded {match.property_type.toLowerCase()} transaction in Dubai is{" "}
        <strong>AED {Math.round(match.avg_price_per_sqft).toLocaleString()} per square foot</strong>,
        computed across {match.transaction_count.toLocaleString()} transactions — not a written
        estimate, every number here is traceable to a real recorded sale.
      </p>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>At a glance</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-text-muted">Average AED/sqft</p>
            <p className="mt-1 font-mono text-lg text-brass">
              {Math.round(match.avg_price_per_sqft).toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-muted">Recorded transactions</p>
            <p className="mt-1 font-mono text-lg text-text-primary">
              {match.transaction_count.toLocaleString()}
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="mt-6">
        <CompsTable comps={comps} />
      </div>

      <p className="mt-6 text-xs text-text-muted">
        Want a defensible valuation for a specific {match.property_type.toLowerCase()}, with a RERA
        compliance check?{" "}
        <Link href="/" className="text-brass underline">
          Ask Sakan AI
        </Link>
        .
      </p>
    </div>
  );
}
