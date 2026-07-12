// Matches comp transaction IDs (TXN-00042) and RERA/DLD clause IDs, both
// single-segment (ESCROW-1, OQOOD-2) and multi-segment (RERA-F-3).
const CITATION_SPLIT_RE = /\b(TXN-[A-Za-z0-9]+|[A-Z]+(?:-[A-Z0-9]+)*-\d+)\b/g;
const CITATION_TEST_RE = /^(TXN-[A-Za-z0-9]+|[A-Z]+(?:-[A-Z0-9]+)*-\d+)$/;

/** Renders text with inline citation tokens (comp transaction IDs, RERA
 * clause IDs) visually distinguished — citations must be visible inline,
 * never hidden behind a click. */
export function CitedText({ text, className }: { text: string; className?: string }) {
  const parts = text.split(CITATION_SPLIT_RE);
  return (
    <span className={className}>
      {parts.map((part, i) =>
        CITATION_TEST_RE.test(part) ? (
          <span key={i} className="rounded bg-brass/10 px-1 font-mono text-[0.85em] text-brass">
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </span>
  );
}
