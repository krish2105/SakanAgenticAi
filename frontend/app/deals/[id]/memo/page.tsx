"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { fetchDealMemo, AuthRequiredError } from "@/lib/api";
import { MemoMarkdown } from "./memo-markdown";
import { ExportPdfButton } from "./export-pdf-button";
import { ShareMemoButton } from "./share-memo-button";

export default function MemoViewerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const [memo, setMemo] = useState<{ memo_markdown: string } | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!token) {
      router.push(`/login?next=${encodeURIComponent(`/deals/${id}/memo`)}`);
      return;
    }

    let cancelled = false;
    fetchDealMemo(id, token)
      .then((result) => {
        if (cancelled) return;
        if (!result) {
          setNotFound(true);
        } else {
          setMemo(result);
        }
      })
      .catch((err) => {
        if (err instanceof AuthRequiredError) {
          router.push(`/login?next=${encodeURIComponent(`/deals/${id}/memo`)}`);
        } else {
          setNotFound(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id, token, authLoading, router]);

  if (authLoading || (!memo && !notFound)) {
    return <div className="px-6 py-8 text-sm text-text-muted">Loading…</div>;
  }

  if (notFound || !memo) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-8">
        <p className="text-sm text-text-muted">
          No memo found for this deal yet — it may still be generating, or belong to a different account.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Link
          href={`/deals/${id}`}
          className="flex items-center gap-1 text-sm text-text-muted hover:text-text-primary"
        >
          <ArrowLeft size={14} />
          Back to deal
        </Link>
        <div className="flex flex-wrap items-start gap-2">
          <ShareMemoButton queryId={id} />
          <ExportPdfButton queryId={id} />
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-border bg-surface p-6 sm:p-8">
        <MemoMarkdown markdown={memo.memo_markdown} />
      </div>
    </div>
  );
}
