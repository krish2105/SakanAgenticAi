import type { MetadataRoute } from "next";
import { fetchMarketSnapshot } from "@/lib/api";
import { communityToSlug } from "@/lib/community-slug";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://sakan-agentic-ai.vercel.app";

// Only the public, marketing-valuable, non-account-scoped, indexable routes.
// Auth flows and deal-specific pages are excluded via robots.ts; the legal
// pages carry their own `robots: { index: false }` (draft, pending review)
// and are deliberately left out here too, for consistency.
const ROUTES = ["/", "/pricing", "/comps", "/market", "/guides"];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const staticEntries: MetadataRoute.Sitemap = ROUTES.map((route) => ({
    url: `${SITE_URL}${route}`,
    lastModified: now,
    changeFrequency: route === "/" ? "daily" : "weekly",
    priority: route === "/" ? 1 : 0.6,
  }));

  // Phase 14: one indexable page per Dubai community, backed by real
  // transaction data (app/guides/[community]/page.tsx). Falls back to just
  // the static routes above if the backend is unreachable at build/request
  // time -- fetchMarketSnapshot already degrades to demo data rather than
  // throwing, so this never breaks the sitemap.
  const snapshot = await fetchMarketSnapshot(20);
  const guideEntries: MetadataRoute.Sitemap = snapshot.map((row) => ({
    url: `${SITE_URL}/guides/${communityToSlug(row.community)}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: 0.5,
  }));

  return [...staticEntries, ...guideEntries];
}
