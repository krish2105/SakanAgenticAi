import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://sakan-agentic-ai.vercel.app";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Auth flows and account-scoped surfaces have no SEO value and shouldn't
      // be indexed or crawled with tokens in the query string.
      disallow: ["/login", "/forgot", "/reset", "/verify", "/account", "/deals"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
