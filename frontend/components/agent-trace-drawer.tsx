"use client";

import { useState } from "react";
import { Check, Loader2, Circle, AlertTriangle, ChevronUp, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLocale } from "@/components/locale-provider";
import type { AgentTraceEntry } from "@/lib/types";

const STEPS: { agent: AgentTraceEntry["agent"]; labelKey: string }[] = [
  { agent: "query", labelKey: "agentTrace.query" },
  { agent: "comps", labelKey: "agentTrace.comps" },
  { agent: "valuation", labelKey: "agentTrace.valuation" },
  { agent: "compliance", labelKey: "agentTrace.compliance" },
  { agent: "memo", labelKey: "agentTrace.memo" },
];

function latestStatusFor(trace: AgentTraceEntry[], agent: string): AgentTraceEntry["status"] | "pending" {
  const entries = trace.filter((t) => t.agent === agent);
  if (entries.length === 0) return "pending";
  return entries[entries.length - 1].status;
}

function StepIcon({ status }: { status: AgentTraceEntry["status"] | "pending" }) {
  if (status === "done") return <Check size={14} className="text-positive" />;
  if (status === "running") return <Loader2 size={14} className="animate-spin text-brass" />;
  if (status === "error") return <AlertTriangle size={14} className="text-negative" />;
  return <Circle size={12} className="text-text-muted" />;
}

function TraceList({ trace, t }: { trace: AgentTraceEntry[]; t: (k: string) => string }) {
  return (
    <ol className="flex flex-col gap-3">
      {STEPS.map((step, i) => {
        const status = latestStatusFor(trace, step.agent);
        const detail = [...trace].reverse().find((t) => t.agent === step.agent && t.detail)?.detail;
        return (
          <li key={step.agent} className="flex items-start gap-3">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border font-mono text-[10px]",
                  status === "done" && "border-positive/50 bg-positive/10",
                  status === "running" && "border-brass/50 bg-brass/10",
                  status === "error" && "border-negative/50 bg-negative/10",
                  status === "pending" && "border-border bg-surface"
                )}
              >
                <StepIcon status={status} />
              </div>
              {i < STEPS.length - 1 && <div className="mt-1 h-6 w-px bg-border" />}
            </div>
            <div className="pt-0.5">
              <div className="text-sm font-medium text-text-primary">
                {i + 1}. {t(step.labelKey)}
              </div>
              {detail && <div className="mt-0.5 max-w-xs text-xs text-text-muted">{detail}</div>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function AgentTraceDrawer({ trace }: { trace: AgentTraceEntry[] }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { t } = useLocale();
  const doneCount = STEPS.filter((s) => latestStatusFor(trace, s.agent) === "done").length;

  return (
    <>
      {/* Desktop: persistent right-column drawer */}
      <aside className="hidden w-72 shrink-0 border-l border-border bg-surface p-4 lg:block">
        <h2 className="font-display text-sm font-medium uppercase tracking-wide text-text-muted">
          {t("agentTrace.title")}
        </h2>
        <div className="mt-4">
          <TraceList trace={trace} t={t} />
        </div>
      </aside>

      {/* Mobile/tablet: bottom sheet */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface-raised shadow-lg lg:hidden">
        <button
          onClick={() => setMobileOpen((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brass"
          aria-expanded={mobileOpen}
        >
          <span className="font-display text-sm font-medium text-text-primary">
            {t("agentTrace.title")} — {doneCount}/{STEPS.length}
          </span>
          {mobileOpen ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
        </button>
        {mobileOpen && (
          <div className="max-h-[50vh] overflow-y-auto border-t border-border px-4 py-4">
            <TraceList trace={trace} t={t} />
          </div>
        )}
      </div>
    </>
  );
}
