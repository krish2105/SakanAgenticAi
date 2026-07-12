"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText } from "lucide-react";
import { AgentTraceDrawer } from "@/components/agent-trace-drawer";
import { CompsTable } from "@/components/comps-table";
import { ValuationCard } from "@/components/valuation-card";
import { ComplianceCard } from "@/components/compliance-card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";
import { dealStreamUrl, fetchDeal, AuthRequiredError } from "@/lib/api";
import type { DealState } from "@/lib/types";

export function DealResultClient({ queryId }: { queryId: string }) {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const [deal, setDeal] = useState<DealState | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [connectionState, setConnectionState] = useState<"connecting" | "open" | "closed">("connecting");
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!token) {
      router.push(`/login?next=${encodeURIComponent(`/deals/${queryId}`)}`);
      return;
    }

    let cancelled = false;
    fetchDeal(queryId, token)
      .then((initial) => {
        if (cancelled) return;
        if (!initial) {
          setNotFound(true);
          return;
        }
        setDeal({
          ...initial,
          query_id: queryId,
          retrieved_comps: initial.retrieved_comps ?? [],
          retrieved_clauses: initial.retrieved_clauses ?? [],
          compliance_flags: initial.compliance_flags ?? [],
          agent_trace: initial.agent_trace ?? [],
        });
      })
      .catch((err) => {
        if (err instanceof AuthRequiredError) {
          router.push(`/login?next=${encodeURIComponent(`/deals/${queryId}`)}`);
        } else {
          setNotFound(true);
        }
      });

    const ws = new WebSocket(dealStreamUrl(queryId, token));
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
  }, [queryId, token, authLoading, router]);

  if (authLoading || (!deal && !notFound)) {
    return <div className="px-6 py-8 text-sm text-text-muted">Loading…</div>;
  }

  if (notFound || !deal) {
    return (
      <div className="px-6 py-8">
        <p className="text-sm text-text-muted">
          This deal doesn&apos;t exist, or doesn&apos;t belong to your account.
        </p>
      </div>
    );
  }

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
