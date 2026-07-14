import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { fetchSharedMemo } from "@/lib/api";
import { MemoMarkdown } from "@/app/deals/[id]/memo/memo-markdown";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ token: string }>;
}): Promise<Metadata> {
  const { token } = await params;
  const memo = await fetchSharedMemo(token);
  if (!memo) return { title: "Shared memo not found" };
  return {
    title: `Deal Memo — ${memo.raw_query}`,
    description: "A shared deal-intelligence memo from Sakan AI: cited comps, valuation, and RERA compliance check.",
    robots: { index: false, follow: false }, // a shared link isn't meant to be indexed/discovered publicly
  };
}

/** Public, unauthenticated -- reachable by anyone holding the link (the
 * token itself is the capability, see backend/app/routers/deals.py's
 * /deals/shared/{token}). Deliberately shows only memo prose, the same
 * scope the backend enforces -- never the full deal_state. */
export default async function SharedMemoPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const memo = await fetchSharedMemo(token);
  if (!memo) notFound();

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="flex items-center justify-between gap-4">
        <p className="font-mono text-xs uppercase tracking-wider text-text-muted">Shared deal memo</p>
        <Link href="/" className="text-xs text-brass underline">
          Ask Sakan AI
        </Link>
      </div>
      <h1 className="mt-1 font-display text-xl font-semibold text-text-primary">{memo.raw_query}</h1>

      <div className="mt-6 rounded-xl border border-border bg-surface p-6 sm:p-8">
        <MemoMarkdown markdown={memo.memo_markdown} />
      </div>

      <p className="mt-6 text-xs text-text-muted">
        Shared read-only via Sakan AI. Want your own defensible valuation with a RERA compliance
        check?{" "}
        <Link href="/" className="text-brass underline">
          Try it free
        </Link>
        .
      </p>
    </div>
  );
}
