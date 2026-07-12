import { ShieldAlert } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CitedText } from "@/components/cited-text";
import type { ComplianceClause } from "@/lib/types";

const UNREVIEWED_CORPUS_FLAG = "unreviewed_regulatory_corpus";

export function ComplianceCard({
  summary,
  flags,
  clauses,
}: {
  summary?: string | null;
  flags: string[];
  clauses: ComplianceClause[];
}) {
  const isUnverified = summary?.toLowerCase().includes("unable to verify");
  const isCorpusUnreviewed = flags.includes(UNREVIEWED_CORPUS_FLAG);
  const otherFlags = flags.filter((f) => f !== UNREVIEWED_CORPUS_FLAG);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Compliance</CardTitle>
      </CardHeader>
      <CardContent>
        {summary ? (
          <p className="text-sm text-text-primary">
            <CitedText text={summary} />
          </p>
        ) : (
          <p className="text-sm text-text-muted">Not yet checked.</p>
        )}

        {isCorpusUnreviewed && (
          <div className="mt-3 flex items-start gap-2 rounded-lg border border-negative/40 bg-negative/10 px-3 py-2">
            <ShieldAlert size={15} className="mt-0.5 shrink-0 text-negative" />
            <p className="text-xs text-text-primary">
              Every clause behind this answer is AI-drafted and has not been reviewed by a licensed
              legal partner. Treat this as a starting point for manual RERA verification, not
              legal advice. See{" "}
              <span className="font-mono text-text-muted">LEGAL_REVIEW.md</span>.
            </p>
          </div>
        )}

        {otherFlags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {otherFlags.map((f) => (
              <Badge key={f} variant={isUnverified ? "negative" : "default"}>
                {f}
              </Badge>
            ))}
          </div>
        )}

        {clauses.length > 0 && (
          <div className="mt-4 border-t border-border pt-3">
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
              Retrieved clauses
            </p>
            <ul className="mt-2 flex flex-col gap-2">
              {clauses.map((c) => (
                <li key={c.clause_id} className="text-xs text-text-muted">
                  <span className="rounded bg-brass/10 px-1 font-mono text-brass">{c.clause_id}</span>{" "}
                  <span>{c.text}</span>
                  <span className="ml-1 text-text-muted/70">({c.source_doc})</span>
                  {c.review_status === "reviewed" && c.reviewed_by ? (
                    <Badge variant="positive" className="ml-1.5 align-middle">
                      reviewed — {c.reviewed_by}
                    </Badge>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
