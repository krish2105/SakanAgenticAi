import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { SiteHeader } from "@/components/site-header";
import { NavRail } from "@/components/nav-rail";
import { MobileNav } from "@/components/mobile-nav";
import { BackendStatusBanner } from "@/components/backend-status-banner";
import { SiteFooter } from "@/components/site-footer";
import { fetchTicker } from "@/lib/api";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://sakan-agentic-ai.vercel.app";

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  weight: ["500", "600"],
  style: ["normal", "italic"],
});

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

const TITLE = "Sakan AI — Deal Intelligence Terminal";
const DESCRIPTION =
  "Agentic real-estate deal intelligence for Dubai: cited comps, defensible valuations, RERA compliance checks, and investor-ready memos.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: TITLE, template: "%s — Sakan AI" },
  description: DESCRIPTION,
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    siteName: "Sakan AI",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: TITLE,
    description: DESCRIPTION,
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const ticks = await fetchTicker();

  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${fraunces.variable} ${plexSans.variable} ${plexMono.variable} h-full`}
    >
      <body className="h-full antialiased">
        <Providers>
          <div className="flex h-full min-h-screen flex-col">
            <SiteHeader ticks={ticks} />
            <BackendStatusBanner />
            <div className="flex flex-1 flex-col">
              <div className="flex flex-1">
                <NavRail />
                {/* pb-16 clears the fixed mobile bottom bar; removed at md+ */}
                <main className="min-w-0 flex-1 pb-16 md:pb-0">{children}</main>
              </div>
              <div className="pb-16 md:pb-0">
                <SiteFooter />
              </div>
            </div>
          </div>
          <MobileNav />
        </Providers>
      </body>
    </html>
  );
}
