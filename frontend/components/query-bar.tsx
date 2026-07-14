"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { capture } from "@/lib/analytics";
import { submitDealQuery, AuthRequiredError } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { useLocale } from "@/components/locale-provider";

const EXAMPLE_QUERIES = [
  "2BR Business Bay under AED 2M",
  "Full memo for a 3BR villa in Arabian Ranches",
  "Check RERA compliance for off-plan Marina Gate II",
  "Value a 1BR in Dubai Marina",
];

export function QueryBar() {
  const router = useRouter();
  const { t } = useLocale();
  const { token, loading: authLoading } = useAuth();
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(query: string) {
    const raw_query = query.trim();
    if (!raw_query || submitting) return;

    if (!token) {
      router.push(`/login?next=${encodeURIComponent("/")}`);
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const { query_id } = await submitDealQuery(raw_query, token);
      capture("deal_query_submitted", { query_length: raw_query.length });
      router.push(`/deals/${query_id}`);
    } catch (err) {
      if (err instanceof AuthRequiredError) {
        router.push(`/login?next=${encodeURIComponent("/")}`);
        return;
      }
      setError(err instanceof Error ? err.message : "Couldn't reach the Sakan AI backend.");
      setSubmitting(false);
    }
  }

  return (
    <div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSubmit(value);
        }}
        className="flex flex-col gap-2 sm:flex-row"
      >
        <div className="relative flex-1">
          <Search size={16} className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={t("query.placeholder")}
            className="h-12 ps-9 font-body text-base"
            aria-label="Deal query"
          />
        </div>
        <Button type="submit" size="lg" disabled={submitting || authLoading}>
          {submitting ? "Running agents..." : token ? t("query.submit") : "Sign in to ask Sakan"}
        </Button>
      </form>

      {error && <p className="mt-2 text-sm text-negative">{error}</p>}
      {!authLoading && !token && (
        <p className="mt-2 text-sm text-text-muted">
          The Comps Explorer is open to everyone — sign in here for the full valuation + compliance + memo pipeline.
        </p>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLE_QUERIES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => {
              setValue(q);
              handleSubmit(q);
            }}
            className="rounded-full border border-border bg-surface px-3 py-1 font-mono text-xs text-text-muted transition-colors hover:border-brass hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brass"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
