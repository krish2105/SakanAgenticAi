import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { fetchDealMemo } from "@/lib/api";
import { MemoMarkdown } from "./memo-markdown";
import { ExportPdfButton } from "./export-pdf-button";

export default async function MemoViewerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const memo = await fetchDealMemo(id);

  if (!memo) {
    notFound();
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="flex items-center justify-between gap-4">
        <Link
          href={`/deals/${id}`}
          className="flex items-center gap-1 text-sm text-text-muted hover:text-text-primary"
        >
          <ArrowLeft size={14} />
          Back to deal
        </Link>
        <ExportPdfButton queryId={id} />
      </div>

      <div className="mt-6 rounded-xl border border-border bg-surface p-6 sm:p-8">
        <MemoMarkdown markdown={memo.memo_markdown} />
      </div>
    </div>
  );
}
