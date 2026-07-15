"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText, RotateCcw } from "lucide-react";
import { AgentTraceDrawer } from "@/components/agent-trace-drawer";
import { CompsTable } from "@/components/comps-table";
import { ValuationCard } from "@/components/valuation-card";
import { ComplianceCard } from "@/components/compliance-card";
import { Button } from "@/components/ui/button";
import { capture } from "@/lib/analytics";
import { useAuth } from "@/components/auth-provider";
import { useLocale } from "@/components/locale-provider";
import { useToast } from "@/components/ui/toast";
import { dealStreamUrl, fetchDeal, retryDealQuery, AuthRequiredError } from "@/lib/api";
import type { DealState } from "@/lib/types";
import { Reveal } from "@/components/motion/reveal";

/** Has the pipeline reached a terminal state for this deal? Used to decide
 * whether there's anything left to stream. comps_search short-circuits after
 * the comps step; every other query type runs through to the memo step. Any
 * error entry is also terminal. */
function isTerminal(deal: DealState): boolean {
  const trace = deal.agent_trace ?? [];
  if (trace.some((t) => t.status === "error")) return true;
  const finalAgent = deal.query_type === "comps_search" ? "comps" : "memo";
  return trace.some((t) => t.agent === finalAgent && t.status === "done");
}

export function DealResultClient({ queryId }: { queryId: string }) {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const { t } = useLocale();
  const { toast } = useToast();
  const [deal, setDeal] = useState<DealState | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [connectionState, setConnectionState] = useState<"connecting" | "open" | "closed">("connecting");
  const [jobFailed, setJobFailed] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  async function handleRetry() {
    if (!token || retrying) return;
    setRetrying(true);
    try {
      await retryDealQuery(queryId, token);
      capture("deal_retry_clicked", { query_id: queryId });
      // Simplest correct way to restart the whole live-tracking effect
      // (fresh fetch + WS connect + reconnection state) cleanly.
      window.location.reload();
    } catch (err) {
      setRetrying(false);
      toast(err instanceof Error ? err.message : "Retry failed", "error");
    }
  }

  useEffect(() => {
    if (authLoading) return;
    if (!token) {
      router.push(`/login?next=${encodeURIComponent(`/deals/${queryId}`)}`);
      return;
    }

    let cancelled = false;
    let completed = false;
    let attempt = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let catchUpTimer: ReturnType<typeof setTimeout> | undefined;

    function normalize(d: DealState): DealState {
      return {
        ...d,
        query_id: queryId,
        retrieved_comps: d.retrieved_comps ?? [],
        retrieved_clauses: d.retrieved_clauses ?? [],
        compliance_flags: d.compliance_flags ?? [],
        agent_trace: d.agent_trace ?? [],
      };
    }

    function connect() {
      if (cancelled || completed || !token) return;
      setConnectionState("connecting");
      const ws = new WebSocket(dealStreamUrl(queryId, token));
      socketRef.current = ws;

      ws.onopen = () => {
        if (cancelled) return;
        attempt = 0;
        setConnectionState("open");
      };
      ws.onmessage = (event) => {
        if (cancelled) return;
        try {
          const message = JSON.parse(event.data);
          if (message.type === "state" || message.type === "complete") {
            setDeal(normalize(message.data as DealState));
          }
          if (message.type === "complete" || message.type === "error") {
            completed = true;
          }
          if (message.type === "error") {
            setJobFailed(true);
          }
        } catch {
          // ignore malformed frames
        }
      };
      ws.onerror = () => {
        // onclose fires next; reconnection is handled there.
      };
      ws.onclose = () => {
        if (cancelled) return;
        if (completed) {
          setConnectionState("closed");
          return;
        }
        // Reconnect with capped exponential backoff (1s, 2s, 4s ... max 15s) --
        // free-tier instances drop idle sockets and cold-start slowly.
        setConnectionState("connecting");
        const delay = Math.min(1000 * 2 ** attempt, 15000);
        attempt += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    }

    fetchDeal(queryId, token)
      .then((initial) => {
        if (cancelled) return;
        if (!initial) {
          setNotFound(true);
          return;
        }
        setDeal(normalize(initial));
        capture("deal_viewed", { query_id: queryId, query_type: initial.query_type });
        if (initial.job_status === "failed") setJobFailed(true);
        if (isTerminal(initial)) {
          // Pipeline already finished before this page loaded -- nothing to
          // stream, so don't open (and endlessly reconnect) a socket.
          completed = true;
          setConnectionState("closed");
          return;
        }
        connect();
        // Safety net: if the "complete" frame was missed (e.g. the pipeline
        // finished in the gap between the initial fetch and the socket
        // connecting), re-fetch once to catch up rather than spin forever.
        catchUpTimer = setTimeout(async () => {
          if (cancelled || completed || !token) return;
          try {
            const latest = await fetchDeal(queryId, token);
            if (cancelled || !latest) return;
            setDeal(normalize(latest));
            if (latest.job_status === "failed") setJobFailed(true);
            if (isTerminal(latest)) {
              completed = true;
              socketRef.current?.close();
              setConnectionState("closed");
            }
          } catch {
            // ignore; the socket path still governs live updates
          }
        }, 20000);
      })
      .catch((err) => {
        if (err instanceof AuthRequiredError) {
          router.push(`/login?next=${encodeURIComponent(`/deals/${queryId}`)}`);
        } else {
          setNotFound(true);
        }
      });

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (catchUpTimer) clearTimeout(catchUpTimer);
      socketRef.current?.close();
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
          <div className="flex items-start justify-between gap-4 animate-in fade-in slide-in-from-top-2 duration-500">
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

          {jobFailed && (
            <div className="mt-4 flex items-center justify-between gap-3 rounded-lg border border-negative/40 bg-negative/10 px-4 py-3">
              <p className="text-sm text-text-primary">{t("agentTrace.failed")}</p>
              <Button size="sm" variant="outline" onClick={handleRetry} disabled={retrying}>
                <RotateCcw size={14} />
                {retrying ? t("agentTrace.retrying") : t("agentTrace.retry")}
              </Button>
            </div>
          )}

          <div className="mt-6 flex flex-col gap-4">
            <Reveal>
              <CompsTable comps={deal.retrieved_comps} />
            </Reveal>
            {deal.query_type !== "comps_search" && (
              <>
                <Reveal delay={0.08}>
                  <ValuationCard
                    low={deal.valuation_low}
                    high={deal.valuation_high}
                    method={deal.valuation_method}
                    rationale={deal.valuation_rationale}
                    comps={deal.retrieved_comps}
                  />
                </Reveal>
                <Reveal delay={0.16}>
                  <ComplianceCard
                    summary={deal.compliance_summary}
                    flags={deal.compliance_flags}
                    clauses={deal.retrieved_clauses}
                  />
                </Reveal>
              </>
            )}
          </div>
        </div>
      </div>

      <AgentTraceDrawer trace={deal.agent_trace} />
    </div>
  );
}
