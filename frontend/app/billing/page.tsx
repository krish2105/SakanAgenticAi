import type { Metadata } from "next";
import { fetchBillingPlans } from "@/lib/api";
import { BillingClient } from "./billing-client";

export const metadata: Metadata = {
  title: "Billing",
  description: "Your Sakan AI plan, usage, and subscription.",
  robots: { index: false },
};

export default async function BillingPage() {
  const plans = await fetchBillingPlans();
  return <BillingClient plans={plans} />;
}
