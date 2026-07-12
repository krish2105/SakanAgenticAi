import type { Comp, DealState, MarketTrendPoint, DeveloperLeaderboardEntry, OffPlanFunnelEntry, Tick } from "@/lib/types";
import { DEMO_TICKS, DEMO_SNAPSHOT, DEMO_COMPS, DEMO_TRENDS, DEMO_LEADERBOARD, DEMO_FUNNEL } from "@/lib/demo-data";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const WS_BASE = API_BASE.replace(/^http/, "ws");

export class AuthRequiredError extends Error {
  constructor() {
    super("Authentication required");
    this.name = "AuthRequiredError";
  }
}

async function safeGet<T>(path: string, fallback: T, init?: RequestInit): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...init, cache: "no-store" });
    if (!res.ok) throw new Error(`${path} -> ${res.status}`);
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

/** Like safeGet, but for endpoints that require auth: a 401 means "not
 * logged in (anymore)" and should send the user to /login, not silently
 * fall back to demo data the way a network blip would. */
async function authedGet<T>(path: string, token: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders(token), cache: "no-store" });
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export async function fetchTicker(): Promise<Tick[]> {
  return safeGet<Tick[]>("/market/ticker", DEMO_TICKS);
}

export async function fetchMarketSnapshot(): Promise<{ community: string; avg_price_per_sqft: number }[]> {
  return safeGet("/market/trends?view=summary", DEMO_SNAPSHOT);
}

export async function fetchMarketTrends(): Promise<MarketTrendPoint[]> {
  return safeGet<MarketTrendPoint[]>("/market/trends?view=timeseries", DEMO_TRENDS);
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

// --- Auth ---

export interface AuthUser {
  user_id: number;
  email: string;
  full_name: string | null;
  role: string;
}

async function parseAuthError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  } catch {
    // fall through
  }
  return `Request failed (${res.status})`;
}

export async function registerUser(email: string, password: string, fullName?: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName || undefined }),
  });
  if (!res.ok) throw new Error(await parseAuthError(res));
  const data = await res.json();
  return data.access_token as string;
}

export async function loginUser(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await parseAuthError(res));
  const data = await res.json();
  return data.access_token as string;
}

export async function fetchMe(token: string): Promise<AuthUser | null> {
  try {
    return await authedGet<AuthUser>("/auth/me", token);
  } catch {
    return null;
  }
}

// --- Deals (all require auth) ---

export async function submitDealQuery(raw_query: string, token: string): Promise<{ query_id: string }> {
  const res = await fetch(`${API_BASE}/deals/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify({ raw_query }),
  });
  if (res.status === 401) throw new AuthRequiredError();
  if (res.status === 429) throw new Error("Too many queries — wait a moment and try again.");
  if (!res.ok) throw new Error(await parseAuthError(res));
  return res.json();
}

export async function fetchDeal(queryId: string, token: string): Promise<DealState | null> {
  try {
    return await authedGet<DealState>(`/deals/${queryId}`, token);
  } catch (err) {
    if (err instanceof AuthRequiredError) throw err;
    return null;
  }
}

export async function fetchDealMemo(queryId: string, token: string): Promise<{ memo_markdown: string } | null> {
  try {
    return await authedGet<{ memo_markdown: string }>(`/deals/${queryId}/memo`, token);
  } catch (err) {
    if (err instanceof AuthRequiredError) throw err;
    return null;
  }
}

export function dealStreamUrl(queryId: string, token: string): string {
  // Browsers can't attach a custom Authorization header to a WebSocket
  // handshake, so the token travels as a query param instead (matches
  // get_current_user_ws on the backend).
  return `${WS_BASE}/ws/deals/${queryId}/stream?token=${encodeURIComponent(token)}`;
}

/** A plain <a href> or window.open can't attach an Authorization header
 * either, so the PDF export is fetched with the header and downloaded as a
 * blob instead of navigated to directly. */
export async function downloadDealMemoPdf(queryId: string, token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/deals/${queryId}/memo?format=pdf`, { headers: authHeaders(token) });
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(await parseAuthError(res));

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `sakan-memo-${queryId}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
