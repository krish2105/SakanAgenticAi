"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { FileText } from "lucide-react";
import { AgentTraceDrawer } from "@/components/agent-trace-drawer";
import { CompsTable } from "@/components/comps-table";
import { ValuationCard } from "@/components/valuation-card";
import { ComplianceCard } from "@/components/compliance-card";
import { Button } from "@/components/ui/button";
import { dealStreamUrl } from "@/lib/api";
import type { DealState } from "@/lib/types";

export function DealResultClient({ queryId, initialDeal }: { queryId: string; initialDeal: DealState }) {
  const [deal, setDeal] = useState<DealState>(initialDeal);
  const [connectionState, setConnectionState] = useState<"connecting" | "open" | "closed">("connecting");
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    const ws = new WebSocket(dealStreamUrl(queryId));
    socketRef.current = ws;

    ws.onopen = () => !cancelled && setConnectionState("open");
    ws.onclose = () => !cancelled && setConnectionState("closed");
    ws.onerror = () => !cancelled && setConnectionState("closed");
    ws.onmessage = (event) => {
      if (cancelled) return;
      try {
        const message = JSON.parse(event.data);
        if (message.type === "state" || message.type === "complete") {
          setDeal(message.data as DealState);
        }
      } catch {
        // ignore malformed frames
      }
    };

    return () => {
      cancelled = true;
      ws.close();
    };
  }, [queryId]);

  return (
    <div className="flex flex-1">
      <div className="min-w-0 flex-1 px-6 py-8 pb-24 lg:pb-8">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-xs text-text-muted">Deal #{queryId}</p>
              <h1 className="mt-1 font-display text-2xl font-semibold text-text-primary">
                {deal.raw_query}
              </h1>
              <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm text-text-muted">
                {deal.community && <span>{deal.community}</span>}
                {deal.property_type && <span>{deal.property_type}</span>}
                {deal.bedrooms != null && <span>{deal.bedrooms}BR</span>}
                {connectionState === "connecting" && <span className="text-brass">connecting…</span>}
                {connectionState === "closed" && <span className="text-text-muted">stream closed</span>}
              </div>
            </div>
            {deal.memo_markdown && (
              <Link href={`/deals/${queryId}/memo`}>
                <Button variant="outline" size="sm">
                  <FileText size={14} />
                  View memo
                </Button>
              </Link>
            )}
          </div>

          <div className="mt-6 flex flex-col gap-4">
            <CompsTable comps={deal.retrieved_comps} />
            {deal.query_type !== "comps_search" && (
              <>
                <ValuationCard
                  low={deal.valuation_low}
                  high={deal.valuation_high}
                  method={deal.valuation_method}
                  rationale={deal.valuation_rationale}
                />
                <ComplianceCard
                  summary={deal.compliance_summary}
                  flags={deal.compliance_flags}
                  clauses={deal.retrieved_clauses}
                />
              </>
            )}
          </div>
        </div>
      </div>

      <AgentTraceDrawer trace={deal.agent_trace} />
    </div>
  );
}
