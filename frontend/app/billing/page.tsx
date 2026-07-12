import { fetchBillingPlans } from "@/lib/api";
import { BillingClient } from "./billing-client";

export default async function BillingPage() {
  const plans = await fetchBillingPlans();
  return <BillingClient plans={plans} />;
}
