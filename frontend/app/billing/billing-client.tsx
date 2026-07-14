"use client";

import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/components/auth-provider";
import { useLocale } from "@/components/locale-provider";
import {
  fetchBillingStatus,
  openBillingPortal,
  startCheckout,
  type BillingPlans,
  type BillingStatus,
} from "@/lib/api";

const TIER_ORDER = ["starter", "pro", "team", "enterprise"] as const;

const FEATURES: Record<(typeof TIER_ORDER)[number], string[]> = {
  starter: ["5 full-pipeline queries / mo", "Unlimited comps search", "Sakan-branded memo export"],
  pro: ["50 full-pipeline queries / mo", "Unlimited comps search", "Unbranded PDF export"],
  team: ["Unmetered full-pipeline queries", "Shared deal history", "Priority data refresh"],
  enterprise: ["API access", "Dedicated compliance corpus", "Custom SLA & SSO"],
};

function formatPrice(aed: number | null): string {
  if (aed === null) return "Custom";
  if (aed === 0) return "Free";
  return `AED ${aed.toLocaleString()}`;
}

export function BillingClient({ plans }: { plans: BillingPlans }) {
  const { t } = useLocale();
  const { token, loading: authLoading } = useAuth();
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [pendingTier, setPendingTier] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    fetchBillingStatus(token).then(setStatus).catch(() => setStatus(null));
  }, [token]);

  async function handleUpgrade(tier: "pro" | "team") {
    if (!token) return;
    setError(null);
    setPendingTier(tier);
    try {
      const url = await startCheckout(tier, token);
      window.location.assign(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start checkout.");
      setPendingTier(null);
    }
  }

  async function handleManage() {
    if (!token) return;
    setError(null);
    try {
      const url = await openBillingPortal(token);
      window.location.assign(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open billing portal.");
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <h1 className="font-display text-2xl font-semibold text-text-primary">{t("billing.title")}</h1>
      <p className="mt-1 text-sm text-text-muted">{t("billing.subtitle")}</p>

      {!authLoading && !token && (
        <p className="mt-4 text-sm text-text-muted">
          <a href="/login" className="text-brass underline">
            {t("billing.logIn")}
          </a>{" "}
          {t("billing.logInPrompt")}
        </p>
      )}

      {status && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>{t("billing.currentPlan")}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Badge>{status.label}</Badge>
              <span className="text-sm text-text-muted">
                {status.monthly_query_limit === null
                  ? `${status.queries_used_this_month} full-pipeline queries this month (unmetered)`
                  : `${status.queries_used_this_month} / ${status.monthly_query_limit} full-pipeline queries this month`}
              </span>
            </div>
            {status.tier !== "starter" && (
              <Button variant="outline" size="sm" onClick={handleManage}>
                {t("billing.manageSubscription")}
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {error && (
        <p role="alert" className="mt-4 rounded-lg border border-red-400/40 bg-red-400/10 px-4 py-2 text-sm text-red-500">
          {error}
        </p>
      )}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {TIER_ORDER.map((tier) => {
          const plan = plans[tier];
          const isCurrent = status?.tier === tier;
          return (
            <Card key={tier} className={isCurrent ? "border-brass" : undefined}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  {plan.label}
                  {isCurrent && <Badge>Current</Badge>}
                </CardTitle>
                <p className="text-2xl font-semibold text-text-primary">
                  {formatPrice(plan.price_aed_monthly)}
                  {plan.price_aed_monthly ? <span className="text-sm font-normal text-text-muted"> /mo</span> : null}
                </p>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <ul className="flex flex-col gap-2 text-sm text-text-muted">
                  {FEATURES[tier].map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <Check size={16} className="mt-0.5 shrink-0 text-brass" />
                      {feature}
                    </li>
                  ))}
                </ul>
                {plan.self_serve_checkout ? (
                  <Button
                    size="sm"
                    disabled={!token || isCurrent || pendingTier === tier}
                    onClick={() => handleUpgrade(tier as "pro" | "team")}
                  >
                    {isCurrent ? "Current plan" : pendingTier === tier ? "Redirecting…" : `Upgrade to ${plan.label}`}
                  </Button>
                ) : tier === "enterprise" ? (
                  <a href="mailto:sales@sakan.ai?subject=Sakan%20AI%20Enterprise" className="w-full">
                    <Button size="sm" variant="outline" className="w-full">
                      Contact sales
                    </Button>
                  </a>
                ) : (
                  <Button size="sm" variant="outline" disabled>
                    Included
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
