import Link from "next/link";
import { MessageSquareText, Sparkles, ShieldCheck, ArrowRight } from "lucide-react";
import { QueryBar } from "@/components/query-bar";
import { MarketSnapshotCards } from "@/components/market-snapshot-cards";
import { T } from "@/components/t";
import { fetchMarketSnapshot } from "@/lib/api";
import { AuroraBackground } from "@/components/motion/aurora-background";
import { Reveal, RevealGroup, RevealItem } from "@/components/motion/reveal";
import { TiltCard } from "@/components/motion/tilt-card";

const STEPS = [
  { icon: MessageSquareText, titleKey: "home.step1Title", bodyKey: "home.step1Body" },
  { icon: Sparkles, titleKey: "home.step2Title", bodyKey: "home.step2Body" },
  { icon: ShieldCheck, titleKey: "home.step3Title", bodyKey: "home.step3Body" },
];

const JSON_LD = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Sakan AI",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  description:
    "Agentic real-estate deal intelligence for Dubai: cited comps, defensible valuations, RERA compliance checks, and investor-ready memos.",
  offers: { "@type": "Offer", price: "0", priceCurrency: "AED" },
};

export default async function Home() {
  const snapshot = await fetchMarketSnapshot();

  return (
    <div className="relative mx-auto max-w-4xl px-6 py-16">
      {/* JSON-LD, statically constructed above -- not user input. */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }} />

      <div className="relative">
        <AuroraBackground className="-inset-x-12 -top-24 h-[420px]" />

        <Reveal>
          <p className="font-mono text-xs uppercase tracking-widest text-brass">
            <T k="home.eyebrow" />
          </p>
        </Reveal>
        <Reveal delay={0.05}>
          <h1 className="mt-2 text-balance font-display text-4xl font-semibold text-text-primary sm:text-5xl">
            <T k="home.title" />
          </h1>
        </Reveal>
        <Reveal delay={0.1}>
          <p className="mt-3 max-w-xl text-text-muted">
            <T k="home.subtitle" />
          </p>
        </Reveal>

        <Reveal delay={0.15}>
          <div className="mt-8">
            <QueryBar />
          </div>
        </Reveal>
      </div>

      <div className="mt-16">
        <h2 className="font-display text-sm font-medium uppercase tracking-wide text-text-muted">
          <T k="home.howItWorks" />
        </h2>
        <RevealGroup className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {STEPS.map(({ icon: Icon, titleKey, bodyKey }, i) => (
            <RevealItem key={titleKey}>
              <TiltCard
                className="h-full"
                wrapperClassName="h-full animate-float-y"
                style={{ animationDelay: `${i * 0.6}s` }}
              >
                <div className="h-full rounded-xl border border-border bg-surface p-4 transition-colors duration-300 hover:border-brass/30">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brass/10 text-brass">
                    <Icon size={18} aria-hidden="true" />
                  </div>
                  <p className="mt-3 font-mono text-xs text-text-muted">0{i + 1}</p>
                  <p className="mt-1 font-medium text-text-primary">
                    <T k={titleKey} />
                  </p>
                  <p className="mt-1 text-sm text-text-muted">
                    <T k={bodyKey} />
                  </p>
                </div>
              </TiltCard>
            </RevealItem>
          ))}
        </RevealGroup>
      </div>

      <div className="mt-12">
        <h2 className="font-display text-sm font-medium uppercase tracking-wide text-text-muted">
          <T k="home.marketSnapshot" />
        </h2>
        <div className="mt-3">
          <MarketSnapshotCards snapshot={snapshot} />
        </div>
      </div>

      <Reveal>
        <div className="mt-12 flex flex-col items-start gap-3 rounded-xl border border-border bg-surface p-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-text-muted">
            <T k="home.pricingTeaser" />
          </p>
          <Link
            href="/pricing"
            className="group inline-flex items-center gap-1.5 text-sm font-medium text-brass hover:text-brass-dim"
          >
            <T k="home.viewPricing" />
            <ArrowRight size={14} aria-hidden="true" className="transition-transform duration-200 group-hover:translate-x-1" />
          </Link>
        </div>
      </Reveal>
    </div>
  );
}
