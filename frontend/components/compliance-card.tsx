import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CitedText } from "@/components/cited-text";
import type { ComplianceClause } from "@/lib/types";

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

        {flags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {flags.map((f) => (
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
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
