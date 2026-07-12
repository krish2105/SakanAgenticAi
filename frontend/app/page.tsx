import { QueryBar } from "@/components/query-bar";
import { MarketSnapshotCards } from "@/components/market-snapshot-cards";
import { T } from "@/components/t";
import { fetchMarketSnapshot } from "@/lib/api";

export default async function Home() {
  const snapshot = await fetchMarketSnapshot();

  return (
    <div className="mx-auto max-w-4xl px-6 py-16">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">
        <T k="home.eyebrow" />
      </p>
      <h1 className="mt-2 font-display text-4xl font-semibold text-text-primary sm:text-5xl">
        <T k="home.title" />
      </h1>
      <p className="mt-3 max-w-xl text-text-muted">
        <T k="home.subtitle" />
      </p>

      <div className="mt-8">
        <QueryBar />
      </div>

      <div className="mt-12">
        <h2 className="font-display text-sm font-medium uppercase tracking-wide text-text-muted">
          <T k="home.marketSnapshot" />
        </h2>
        <div className="mt-3">
          <MarketSnapshotCards snapshot={snapshot} />
        </div>
      </div>
    </div>
  );
}
