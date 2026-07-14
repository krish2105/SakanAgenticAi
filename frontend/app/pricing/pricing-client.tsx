"use client";

import Link from "next/link";
import { Check } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { T } from "@/components/t";
import { useLocale } from "@/components/locale-provider";
import type { BillingPlans } from "@/lib/api";

const TIER_ORDER = ["starter", "pro", "team", "enterprise"] as const;

const FEATURES: Record<(typeof TIER_ORDER)[number], string[]> = {
  starter: ["5 full-pipeline queries / mo", "Unlimited comps search", "Sakan-branded memo export"],
  pro: ["50 full-pipeline queries / mo", "Unlimited comps search", "Unbranded PDF export"],
  team: ["Unmetered full-pipeline queries", "Shared deal history", "Priority data refresh"],
  enterprise: ["API access", "Dedicated compliance corpus", "Custom SLA & SSO"],
};

const FAQS = [
  {
    q: "Is the compliance check a substitute for legal advice?",
    a: "No. Sakan cites the regulatory clauses behind every compliance answer, but the corpus is a demonstration set unless a given deployment has completed a formal legal review — see the disclaimer on every deal result.",
  },
  {
    q: "What counts as a \"full-pipeline query\"?",
    a: "A query that runs the full Comps → Valuation → Compliance → Memo pipeline. Plain comps search (no valuation/compliance/memo) is unmetered on every plan.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes — cancel from the billing portal at any time. You keep access until the end of your current billing period.",
  },
  {
    q: "Is my data used to train models?",
    a: "No. See our Privacy Policy and Data Processing Addendum for exactly what's collected and how it's used.",
  },
];

function formatPrice(aed: number | null): string {
  if (aed === null) return "Custom";
  if (aed === 0) return "Free";
  return `AED ${aed.toLocaleString()}`;
}

export function PricingClient({ plans }: { plans: BillingPlans }) {
  const { t } = useLocale();

  return (
    <div className="mx-auto max-w-5xl px-6 py-16">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">
        <T k="pricing.eyebrow" />
      </p>
      <h1 className="mt-2 font-display text-4xl font-semibold text-text-primary sm:text-5xl">
        <T k="pricing.title" />
      </h1>
      <p className="mt-3 max-w-xl text-text-muted">
        <T k="pricing.subtitle" />
      </p>

      <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {TIER_ORDER.map((tier) => {
          const plan = plans[tier];
          const isEnterprise = tier === "enterprise";
          return (
            <Card key={tier} className={tier === "pro" ? "border-brass" : undefined}>
              <CardHeader>
                <CardTitle>{plan.label}</CardTitle>
                <p className="text-2xl font-semibold text-text-primary">
                  {formatPrice(plan.price_aed_monthly)}
                  {plan.price_aed_monthly ? (
                    <span className="text-sm font-normal text-text-muted"> /mo</span>
                  ) : null}
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
                {isEnterprise ? (
                  <a href="mailto:sales@sakan.ai?subject=Sakan%20AI%20Enterprise">
                    <Button size="sm" variant="outline" className="w-full">
                      <T k="pricing.contactSales" />
                    </Button>
                  </a>
                ) : (
                  <Link href={`/login?next=${encodeURIComponent("/billing")}`}>
                    <Button size="sm" className="w-full">
                      <T k="pricing.getStarted" />
                    </Button>
                  </Link>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="mt-16">
        <h2 className="font-display text-xl font-semibold text-text-primary">{t("pricing.faqTitle")}</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {FAQS.map((faq) => (
            <div key={faq.q} className="rounded-xl border border-border bg-surface p-4">
              <p className="font-medium text-text-primary">{faq.q}</p>
              <p className="mt-1.5 text-sm text-text-muted">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
