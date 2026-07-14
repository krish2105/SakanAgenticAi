import { AlertTriangle } from "lucide-react";
import { T } from "@/components/t";

/** Every legal page must carry this. Matches the project's established
 * honesty pattern (LEGAL_REVIEW.md: every regulatory clause is
 * review_status: unreviewed until counsel signs off) -- these templates are
 * the same category of "not yet reviewed," and must say so loudly, not in
 * fine print. See the Revenue Unlock Gate: counsel review is a prerequisite
 * for charging real customers, not optional polish. */
export function LegalDraftBanner() {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-negative/40 bg-negative/10 px-4 py-3"
    >
      <AlertTriangle size={18} className="mt-0.5 shrink-0 text-negative" />
      <p className="text-sm text-text-primary">
        <T k="legal.draftBanner" />
      </p>
    </div>
  );
}
