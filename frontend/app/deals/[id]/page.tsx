import { notFound } from "next/navigation";
import { fetchDeal } from "@/lib/api";
import { DealResultClient } from "./deal-result-client";
import type { DealState } from "@/lib/types";

export default async function DealResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const deal = await fetchDeal(id);

  if (!deal) {
    notFound();
  }

  const initialDeal: DealState = {
    ...deal,
    query_id: id,
    retrieved_comps: deal.retrieved_comps ?? [],
    retrieved_clauses: deal.retrieved_clauses ?? [],
    compliance_flags: deal.compliance_flags ?? [],
    agent_trace: deal.agent_trace ?? [],
  };

  return <DealResultClient queryId={id} initialDeal={initialDeal} />;
}
