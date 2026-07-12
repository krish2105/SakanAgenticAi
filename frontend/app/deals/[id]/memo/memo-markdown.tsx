"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function MemoMarkdown({ markdown }: { markdown: string }) {
  return (
    <article
      className="prose prose-sm max-w-none font-body text-text-primary
        prose-headings:font-display prose-headings:text-text-primary
        prose-p:text-text-primary prose-strong:text-text-primary
        prose-table:font-mono prose-table:text-xs
        prose-th:text-text-muted prose-td:text-text-primary
        prose-a:text-brass"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
    </article>
  );
}
