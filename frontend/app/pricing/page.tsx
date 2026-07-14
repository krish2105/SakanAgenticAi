import type { Metadata } from "next";
import { fetchBillingPlans } from "@/lib/api";
import { PricingClient } from "./pricing-client";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Simple, transparent pricing for Sakan AI's deal-intelligence platform. Start free with unlimited comps search.",
};

export default async function PricingPage() {
  const plans = await fetchBillingPlans();
  return <PricingClient plans={plans} />;
}
