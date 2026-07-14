import type { Comp, DealState, DealSummary, MarketTrendPoint, DeveloperLeaderboardEntry, OffPlanFunnelEntry, Tick } from "@/lib/types";
import { DEMO_TICKS, DEMO_SNAPSHOT, DEMO_COMPS, DEMO_TRENDS, DEMO_LEADERBOARD, DEMO_FUNNEL } from "@/lib/demo-data";

/** Strips a trailing slash so a misconfigured NEXT_PUBLIC_API_URL (a very
 * easy copy-paste mistake, e.g. "https://api.example.com/") can't turn every
 * request into a double-slash path like ".../auth/login" -- FastAPI/Starlette
 * 404s on that instead of matching the route, and the JSON body of that 404
 * ({"detail":"Not Found"}) is indistinguishable from a real auth error once
 * it reaches parseAuthError below. */
export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");
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

// --- Token storage + silent refresh ---------------------------------------
//
// Access tokens are short-lived (backend Phase 3). The stored refresh token is
// exchanged transparently on a 401, so the user isn't bounced to /login every
// hour. localStorage is the single source of truth; the auth provider mirrors
// it into React state via onTokenChange.

const ACCESS_KEY = "sakan_token";
const REFRESH_KEY = "sakan_refresh_token";

type TokenListener = (accessToken: string | null) => void;
const tokenListeners = new Set<TokenListener>();

export function onTokenChange(listener: TokenListener): () => void {
  tokenListeners.add(listener);
  return () => {
    tokenListeners.delete(listener);
  };
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(accessToken: string, refreshToken?: string | null): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_KEY, accessToken);
  if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
  tokenListeners.forEach((fn) => fn(accessToken));
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  tokenListeners.forEach((fn) => fn(null));
}

let refreshInFlight: Promise<string | null> | null = null;

/** Exchange the refresh token for a new access token. Deduped: concurrent 401s
 * share one refresh request. Returns the new access token, or null (and clears
 * storage) if the refresh token is gone/invalid. */
async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) {
        clearTokens();
        return null;
      }
      const data = await res.json();
      setTokens(data.access_token, data.refresh_token);
      return data.access_token as string;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

/** Authenticated fetch with transparent one-shot refresh on 401. Prefers the
 * stored access token (kept fresh by refresh) over any token a caller passes,
 * so a background refresh benefits every subsequent call. */
async function authedFetch(path: string, init: RequestInit = {}, token?: string): Promise<Response> {
  const access = getAccessToken() || token || "";
  const doFetch = (bearer: string) =>
    fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { ...(init.headers || {}), ...authHeaders(bearer) },
      cache: "no-store",
    });

  let res = await doFetch(access);
  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) res = await doFetch(refreshed);
  }
  return res;
}

/** Like safeGet, but for endpoints that require auth: a still-401 (even after a
 * refresh attempt) means "not logged in anymore" and should send the user to
 * /login, not silently fall back to demo data. */
async function authedGet<T>(path: string, token: string): Promise<T> {
  const res = await authedFetch(path, { method: "GET" }, token);
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export async function fetchTicker(): Promise<Tick[]> {
  return safeGet<Tick[]>("/market/ticker", DEMO_TICKS);
}

export async function fetchMarketSnapshot(
  limit = 4
): Promise<{ community: string; avg_price_per_sqft: number }[]> {
  return safeGet(`/market/trends?view=summary&limit=${limit}`, DEMO_SNAPSHOT);
}

export async function fetchMarketTrends(): Promise<MarketTrendPoint[]> {
  return safeGet<MarketTrendPoint[]>("/market/trends?view=timeseries", DEMO_TRENDS);
}

/** Phase 14: per-community trend data + a comps sample, feeding the
 * /guides/[community] SEO content pages -- real seeded data, never
 * fabricated prose, matching the rest of this product's "every claim
 * shows its work" posture. */
export async function fetchCommunityTrend(community: string): Promise<MarketTrendPoint[]> {
  return safeGet<MarketTrendPoint[]>(
    `/market/trends?view=timeseries&community=${encodeURIComponent(community)}`,
    []
  );
}

export async function fetchDeveloperLeaderboard(): Promise<DeveloperLeaderboardEntry[]> {
  return safeGet<DeveloperLeaderboardEntry[]>("/market/developers", DEMO_LEADERBOARD);
}

export async function fetchOffPlanFunnel(): Promise<OffPlanFunnelEntry[]> {
  return safeGet<OffPlanFunnelEntry[]>("/market/off-plan-funnel", DEMO_FUNNEL);
}

export interface PropertyTypeSnapshot {
  property_type: string;
  avg_price_per_sqft: number;
  transaction_count: number;
}

/** Phase 19: powers /guides/type/[propertyType], the property-type
 * counterpart to Phase 14's per-community guide pages -- same real,
 * never-fabricated data posture. */
export async function fetchPropertyTypeSnapshot(): Promise<PropertyTypeSnapshot[]> {
  return safeGet<PropertyTypeSnapshot[]>("/market/trends?view=property_type", []);
}

// --- Status page (Phase 18) ---

export interface ReadinessCheck {
  ok: boolean;
  detail: string;
}

export interface ReadinessReport {
  reachable: boolean;
  ready: boolean;
  checks: Record<string, ReadinessCheck>;
}

/** Unlike safeGet, a non-2xx response (readyz returns 503 when not ready) is
 * real data here, not a failure to fall back from -- only an unreachable
 * backend (network error) counts as "reachable: false". */
export async function fetchReadiness(): Promise<ReadinessReport> {
  try {
    const res = await fetch(`${API_BASE}/readyz`, { cache: "no-store" });
    const body = await res.json();
    return { reachable: true, ready: Boolean(body.ready), checks: body.checks || {} };
  } catch {
    return { reachable: false, ready: false, checks: {} };
  }
}

export async function fetchComps(params: Record<string, string | number | undefined>): Promise<Comp[]> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return safeGet<Comp[]>(`/comps?${qs.toString()}`, DEMO_COMPS);
}

// --- Saved comps / watchlist ---

export async function fetchSavedComps(token: string): Promise<Comp[]> {
  return authedGet<Comp[]>("/comps/saved", token);
}

/** Idempotent server-side -- safe to call even if the UI's local "is this
 * saved" state is stale. */
export async function saveComp(transactionId: string, token: string): Promise<void> {
  const res = await authedFetch(
    "/comps/saved",
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ transaction_id: transactionId }) },
    token
  );
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(await parseAuthError(res));
}

export async function unsaveComp(transactionId: string, token: string): Promise<void> {
  const res = await authedFetch(`/comps/saved/${transactionId}`, { method: "DELETE" }, token);
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok && res.status !== 204) throw new Error(await parseAuthError(res));
}

// --- Auth ---

export interface AuthUser {
  user_id: number;
  email: string;
  full_name: string | null;
  role: string;
  email_verified?: boolean;
}

/** `routingNeverA404` is for endpoints that can never legitimately 404 for a
 * real application reason (login/register/demo aren't scoped to a resource
 * that might not exist) -- there, a bare 404 means the request didn't reach
 * the route at all (wrong NEXT_PUBLIC_API_URL, a stale deploy, a proxy
 * misrouting the path), and FastAPI's default 404 body ({"detail":"Not
 * Found"}) would otherwise pass straight through and read exactly like a
 * real credential error. Endpoints where a 404 IS meaningful (e.g. inviting
 * an email with no account) must leave this off. */
async function parseAuthError(res: Response, routingNeverA404 = false): Promise<string> {
  if (routingNeverA404 && res.status === 404) {
    return "Couldn't reach the sign-in service (unexpected 404). This usually means the app is misconfigured, not that your credentials are wrong.";
  }
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  } catch {
    // fall through
  }
  return `Request failed (${res.status})`;
}

export async function registerUser(
  email: string,
  password: string,
  fullName?: string,
  turnstileToken?: string
): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password,
      full_name: fullName || undefined,
      turnstile_token: turnstileToken || undefined,
    }),
  });
  if (!res.ok) throw new Error(await parseAuthError(res, true));
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data.access_token as string;
}

export async function loginUser(email: string, password: string, turnstileToken?: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, turnstile_token: turnstileToken || undefined }),
  });
  if (!res.ok) throw new Error(await parseAuthError(res, true));
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data.access_token as string;
}

/** "Continue as Demo" -- a fresh, real ephemeral account created server-side
 * (backend/app/routers/auth.py's /auth/demo), not a canned/fake session. No
 * email or password needed; every call gets its own full Starter-tier quota. */
export async function startDemoSession(): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/demo`, { method: "POST" });
  if (!res.ok) throw new Error(await parseAuthError(res, true));
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data.access_token as string;
}

/** Revoke the refresh token server-side, then clear local storage. */
export async function logoutUser(): Promise<void> {
  const refreshToken = getRefreshToken();
  if (refreshToken) {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch {
      // best-effort; clear locally regardless
    }
  }
  clearTokens();
}

export async function requestPasswordReset(email: string): Promise<void> {
  // Always resolves (backend returns 202 whether or not the email exists).
  await fetch(`${API_BASE}/auth/forgot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  if (!res.ok) throw new Error(await parseAuthError(res));
}

export async function verifyEmail(token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) throw new Error(await parseAuthError(res));
}

export async function fetchMe(token: string): Promise<AuthUser | null> {
  try {
    return await authedGet<AuthUser>("/auth/me", token);
  } catch {
    return null;
  }
}

// --- Active sessions (Phase 16) ---

export interface AuthSession {
  id: number;
  user_agent: string | null;
  ip_address: string | null;
  created_at: string;
  last_used_at: string | null;
}

export async function fetchSessions(token: string): Promise<AuthSession[]> {
  return authedGet<AuthSession[]>("/auth/sessions", token);
}

export async function revokeSession(sessionId: number, token: string): Promise<void> {
  const res = await authedFetch(`/auth/sessions/${sessionId}`, { method: "DELETE" }, token);
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(await parseAuthError(res));
}

/** Logs every device out, including the one making this call -- callers
 * should follow up with a local logout()/redirect, same as the backend
 * revokes the calling session's own refresh token along with the rest. */
export async function revokeAllSessions(token: string): Promise<void> {
  const res = await authedFetch("/auth/sessions/revoke-all", { method: "POST" }, token);
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(await parseAuthError(res));
}

// --- Partner API keys (Phase 20) ---

export interface ApiKeySummary {
  id: number;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyCreated extends ApiKeySummary {
  api_key: string; // only ever present in the create response, shown once
}

export async function fetchApiKeys(token: string): Promise<ApiKeySummary[]> {
  return authedGet<ApiKeySummary[]>("/partner/api-keys", token);
}

export async function createApiKey(name: string, token: string): Promise<ApiKeyCreated> {
  const res = await authedFetch(
    "/partner/api-keys",
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) },
    token
  );
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(await parseAuthError(res));
  return res.json();
}

export async function revokeApiKey(apiKeyId: number, token: string): Promise<void> {
  const res = await authedFetch(`/partner/api-keys/${apiKeyId}`, { method: "DELETE" }, token);
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(await parseAuthError(res));
}

// --- Deals (all require auth) ---

export async function submitDealQuery(raw_query: string, token: string): Promise<{ query_id: string }> {
  const res = await authedFetch(
    "/deals/query",
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ raw_query }) },
    token
  );
  if (res.status === 401) throw new AuthRequiredError();
  if (res.status === 429) throw new Error("Too many queries — wait a moment and try again.");
  if (!res.ok) throw new Error(await parseAuthError(res));
  return res.json();
}

/** Re-runs a deal query that previously failed (job_status === "failed").
 * Free: quota is charged once at creation, never per retry attempt. */
export async function retryDealQuery(queryId: string, token: string): Promise<{ query_id: string }> {
  const res = await authedFetch(`/deals/${queryId}/retry`, { method: "POST" }, token);
  if (res.status === 401) throw new AuthRequiredError();
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

// --- Shareable public memo links ---

export interface ShareLink {
  share_token: string;
  share_url: string;
}

/** Idempotent server-side (same deal always returns the same token until
 * revoked), so it's safe to call every time the share UI opens rather than
 * tracking share state locally. */
export async function createMemoShareLink(queryId: string, token: string): Promise<ShareLink> {
  const res = await authedFetch(`/deals/${queryId}/share`, { method: "POST" }, token);
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(await parseAuthError(res));
  return res.json();
}

export async function revokeMemoShareLink(queryId: string, token: string): Promise<void> {
  const res = await authedFetch(`/deals/${queryId}/share`, { method: "DELETE" }, token);
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok && res.status !== 204) throw new Error(await parseAuthError(res));
}

export interface SharedMemo {
  memo_markdown: string;
  raw_query: string;
  created_at: string | null;
}

/** No auth -- this is the public read path a share link's recipient hits. */
export async function fetchSharedMemo(shareToken: string): Promise<SharedMemo | null> {
  const res = await fetch(`${API_BASE}/deals/shared/${shareToken}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchDeals(
  token: string,
  { limit = 20, offset = 0 }: { limit?: number; offset?: number } = {}
): Promise<DealSummary[]> {
  const res = await authedGet<{ deals: DealSummary[] }>(
    `/deals?limit=${limit}&offset=${offset}`,
    token
  );
  return res.deals;
}

export function dealStreamUrl(queryId: string, token: string): string {
  // Browsers can't attach a custom Authorization header to a WebSocket
  // handshake, so the token travels as a query param instead (matches
  // get_current_user_ws on the backend).
  return `${WS_BASE}/ws/deals/${queryId}/stream?token=${encodeURIComponent(token)}`;
}

// --- Billing (Phase B) ---

export interface BillingPlan {
  label: string;
  price_aed_monthly: number | null; // null = "custom" (Enterprise)
  monthly_query_limit: number | null; // null = unmetered
  self_serve_checkout: boolean;
}

export type BillingPlans = Record<"starter" | "pro" | "team" | "enterprise", BillingPlan>;

export interface BillingStatus {
  tier: string;
  label: string;
  monthly_query_limit: number | null;
  queries_used_this_month: number;
  queries_remaining: number | null;
  subscription_status: string | null;
}

const DEMO_PLANS: BillingPlans = {
  starter: { label: "Starter", price_aed_monthly: 0, monthly_query_limit: 5, self_serve_checkout: false },
  pro: { label: "Pro", price_aed_monthly: 299, monthly_query_limit: 50, self_serve_checkout: true },
  team: { label: "Team", price_aed_monthly: 999, monthly_query_limit: null, self_serve_checkout: true },
  enterprise: { label: "Enterprise", price_aed_monthly: null, monthly_query_limit: null, self_serve_checkout: false },
};

export async function fetchBillingPlans(): Promise<BillingPlans> {
  return safeGet<BillingPlans>("/billing/plans", DEMO_PLANS);
}

export async function fetchBillingStatus(token: string): Promise<BillingStatus | null> {
  try {
    return await authedGet<BillingStatus>("/billing/me", token);
  } catch (err) {
    if (err instanceof AuthRequiredError) throw err;
    return null;
  }
}

export async function startCheckout(tier: "pro" | "team", token: string): Promise<string> {
  const res = await authedFetch(
    "/billing/checkout",
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tier }) },
    token
  );
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(await parseAuthError(res));
  const data = await res.json();
  return data.checkout_url as string;
}

export async function openBillingPortal(token: string): Promise<string> {
  const res = await authedFetch("/billing/portal", { method: "POST" }, token);
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(await parseAuthError(res));
  const data = await res.json();
  return data.portal_url as string;
}

/** A plain <a href> or window.open can't attach an Authorization header
 * either, so the PDF export is fetched with the header and downloaded as a
 * blob instead of navigated to directly. */
export async function downloadDealMemoPdf(queryId: string, token: string): Promise<void> {
  const res = await authedFetch(`/deals/${queryId}/memo?format=pdf`, { method: "GET" }, token);
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

// --- Admin (Phase 10b) -------------------------------------------------

export interface AdminStats {
  total_users: number;
  verified_users: number;
  total_deals: number;
  users_by_tier: Record<string, number>;
}

export interface AdminUser {
  user_id: number;
  email: string;
  full_name: string | null;
  role: string;
  tier: string;
  email_verified: boolean;
  subscription_status: string | null;
  created_at: string | null;
}

export interface AdminUsersPage {
  total: number;
  limit: number;
  offset: number;
  users: AdminUser[];
}

export interface AdminQueryVolumeDay {
  day: string;
  count: number;
}

/** All four admin_* functions throw AuthRequiredError on a 401 (same as
 * authedGet) and a generic Error on a 403 (not signed in as an Admin) --
 * callers distinguish "not logged in" from "logged in but not authorized". */
export async function fetchAdminStats(token: string): Promise<AdminStats> {
  return authedGet<AdminStats>("/admin/stats", token);
}

export async function fetchAdminUsers(
  token: string,
  { q, limit = 25, offset = 0 }: { q?: string; limit?: number; offset?: number } = {}
): Promise<AdminUsersPage> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (q) params.set("q", q);
  return authedGet<AdminUsersPage>(`/admin/users?${params.toString()}`, token);
}

export async function setAdminUserTier(userId: number, tier: string, token: string): Promise<AdminUser> {
  const res = await authedFetch(
    `/admin/users/${userId}/tier`,
    { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tier }) },
    token
  );
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(await parseAuthError(res));
  return res.json();
}

export async function fetchAdminQueryVolume(token: string, days = 30): Promise<AdminQueryVolumeDay[]> {
  return authedGet<AdminQueryVolumeDay[]>(`/admin/query-volume?days=${days}`, token);
}

// --- Team billing (Phase 11c) -------------------------------------------

export interface TeamMember {
  user_id: number;
  email: string;
  full_name: string | null;
  is_owner: boolean;
}

async function teamPost<T>(path: string, body: unknown, token: string): Promise<T> {
  const res = await authedFetch(
    path,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
    token
  );
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(await parseAuthError(res));
  return res.json();
}

export async function inviteTeamMember(email: string, token: string): Promise<{ invited_user_id: number }> {
  return teamPost("/billing/team/invite", { email }, token);
}

export async function acceptTeamInvite(
  inviteToken: string,
  token: string
): Promise<{ organization_id: number; seat_count: number }> {
  return teamPost("/billing/team/accept", { token: inviteToken }, token);
}

/** Returns null (rather than throwing) when the caller isn't on a team --
 * that's the common case for every non-Team-tier user viewing /billing. */
export async function fetchTeamMembers(token: string): Promise<TeamMember[] | null> {
  try {
    return await authedGet<TeamMember[]>("/billing/team/members", token);
  } catch (err) {
    if (err instanceof AuthRequiredError) throw err;
    return null;
  }
}

export async function removeTeamMember(userId: number, token: string): Promise<void> {
  const res = await authedFetch(`/billing/team/members/${userId}`, { method: "DELETE" }, token);
  if (res.status === 401) throw new AuthRequiredError();
  if (!res.ok) throw new Error(await parseAuthError(res));
}
