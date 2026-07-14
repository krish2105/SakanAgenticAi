import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://sakan-agentic-ai.vercel.app";

// Only the public, marketing-valuable, non-account-scoped, indexable routes.
// Auth flows and deal-specific pages are excluded via robots.ts; the legal
// pages carry their own `robots: { index: false }` (draft, pending review)
// and are deliberately left out here too, for consistency.
const ROUTES = ["/", "/pricing", "/comps", "/market"];

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return ROUTES.map((route) => ({
    url: `${SITE_URL}${route}`,
    lastModified: now,
    changeFrequency: route === "/" ? "daily" : "weekly",
    priority: route === "/" ? 1 : 0.6,
  }));
}
