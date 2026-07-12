import { QueryBar } from "@/components/query-bar";
import { MarketSnapshotCards } from "@/components/market-snapshot-cards";
import { fetchMarketSnapshot } from "@/lib/api";

export default async function Home() {
  const snapshot = await fetchMarketSnapshot();

  return (
    <div className="mx-auto max-w-4xl px-6 py-16">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">Deal Intelligence Terminal</p>
      <h1 className="mt-2 font-display text-4xl font-semibold text-text-primary sm:text-5xl">
        Ask Sakan a deal question.
      </h1>
      <p className="mt-3 max-w-xl text-text-muted">
        Plain English in — cited comps, a defensible valuation, a RERA compliance check, and a
        ready-to-send memo out. Every claim shows its work.
      </p>

      <div className="mt-8">
        <QueryBar />
      </div>

      <div className="mt-12">
        <h2 className="font-display text-sm font-medium uppercase tracking-wide text-text-muted">
          Market snapshot
        </h2>
        <div className="mt-3">
          <MarketSnapshotCards snapshot={snapshot} />
        </div>
      </div>
    </div>
  );
}
