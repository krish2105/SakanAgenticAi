import type { Comp, DealState, MarketTrendPoint, DeveloperLeaderboardEntry, OffPlanFunnelEntry, Tick } from "@/lib/types";
import { DEMO_TICKS, DEMO_SNAPSHOT, DEMO_COMPS, DEMO_TRENDS, DEMO_LEADERBOARD, DEMO_FUNNEL } from "@/lib/demo-data";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const WS_BASE = API_BASE.replace(/^http/, "ws");

async function safeGet<T>(path: string, fallback: T, init?: RequestInit): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...init, cache: "no-store" });
    if (!res.ok) throw new Error(`${path} -> ${res.status}`);
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export async function fetchTicker(): Promise<Tick[]> {
  return safeGet<Tick[]>("/market/ticker", DEMO_TICKS);
}

export async function fetchMarketSnapshot(): Promise<{ community: string; avg_price_per_sqft: number }[]> {
  return safeGet("/market/trends?summary=true", DEMO_SNAPSHOT);
}

export async function fetchMarketTrends(): Promise<MarketTrendPoint[]> {
  return safeGet<MarketTrendPoint[]>("/market/trends", DEMO_TRENDS);
}

export async function fetchDeveloperLeaderboard(): Promise<DeveloperLeaderboardEntry[]> {
  return safeGet<DeveloperLeaderboardEntry[]>("/market/developers", DEMO_LEADERBOARD);
}

export async function fetchOffPlanFunnel(): Promise<OffPlanFunnelEntry[]> {
  return safeGet<OffPlanFunnelEntry[]>("/market/off-plan-funnel", DEMO_FUNNEL);
}

export async function fetchComps(params: Record<string, string | number | undefined>): Promise<Comp[]> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return safeGet<Comp[]>(`/comps?${qs.toString()}`, DEMO_COMPS);
}

export async function submitDealQuery(raw_query: string): Promise<{ query_id: string }> {
  const res = await fetch(`${API_BASE}/deals/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_query }),
  });
  if (!res.ok) throw new Error(`Query submission failed: ${res.status}`);
  return res.json();
}

export async function fetchDeal(queryId: string): Promise<DealState | null> {
  return safeGet<DealState | null>(`/deals/${queryId}`, null);
}

export async function fetchDealMemo(queryId: string): Promise<{ memo_markdown: string } | null> {
  return safeGet<{ memo_markdown: string } | null>(`/deals/${queryId}/memo`, null);
}

export function dealStreamUrl(queryId: string): string {
  return `${WS_BASE}/ws/deals/${queryId}/stream`;
}
