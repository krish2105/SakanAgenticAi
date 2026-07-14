/**
 * Thin wrapper around the Sakan AI backend, shared by popup.js and
 * content.js. Mirrors frontend/lib/api.ts's shape loosely but is
 * deliberately not a copy -- this extension is a separate, smaller
 * surface (comps search + kicking off a full deal check), not a port of
 * the whole web app.
 */
const SakanAPI = (() => {
  const DEFAULT_BACKEND_URL = "http://localhost:8000";
  const TOKEN_KEY = "sakan_ext_token";
  const REFRESH_TOKEN_KEY = "sakan_ext_refresh_token";
  const BACKEND_URL_KEY = "sakan_ext_backend_url";

  async function getBackendUrl() {
    const { [BACKEND_URL_KEY]: url } = await chrome.storage.local.get(BACKEND_URL_KEY);
    return url || DEFAULT_BACKEND_URL;
  }

  async function setBackendUrl(url) {
    await chrome.storage.local.set({ [BACKEND_URL_KEY]: url });
  }

  async function getToken() {
    const { [TOKEN_KEY]: token } = await chrome.storage.local.get(TOKEN_KEY);
    return token || null;
  }

  async function getRefreshToken() {
    const { [REFRESH_TOKEN_KEY]: token } = await chrome.storage.local.get(REFRESH_TOKEN_KEY);
    return token || null;
  }

  async function setTokens(accessToken, refreshToken) {
    await chrome.storage.local.set({ [TOKEN_KEY]: accessToken, [REFRESH_TOKEN_KEY]: refreshToken });
  }

  async function clearToken() {
    await chrome.storage.local.remove([TOKEN_KEY, REFRESH_TOKEN_KEY]);
  }

  async function login(email, password) {
    const base = await getBackendUrl();
    const res = await fetch(`${base}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Login failed (${res.status})`);
    }
    const data = await res.json();
    await setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  }

  /** One-shot silent refresh: exchanges the stored refresh token for a new
   * access/refresh pair (the backend rotates refresh tokens on every use --
   * see app/routers/auth.py's /refresh). Access tokens are short-lived
   * (Phase 3 of the MVP roadmap, 60 minutes by default) so without this a
   * session signed in more than an hour ago would 401 on its next call and
   * force a fresh sign-in every time. Returns the new access token, or null
   * if the refresh token is itself invalid/expired (caller should treat
   * that as "signed out"). */
  async function refreshAccessToken() {
    const refreshToken = await getRefreshToken();
    if (!refreshToken) return null;
    const base = await getBackendUrl();
    const res = await fetch(`${base}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      await clearToken();
      return null;
    }
    const data = await res.json();
    await setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  }

  /** Wraps an authenticated fetch with a single silent-refresh retry on 401
   * -- mirrors frontend/lib/api.ts's authedFetch, scaled down to this
   * extension's much smaller API surface (two authenticated calls). */
  async function authedFetch(path, init = {}) {
    const base = await getBackendUrl();
    let token = await getToken();
    const doFetch = (bearer) =>
      fetch(`${base}${path}`, { ...init, headers: { ...(init.headers || {}), Authorization: `Bearer ${bearer}` } });

    let res = await doFetch(token || "");
    if (res.status === 401) {
      const refreshed = await refreshAccessToken();
      if (refreshed) res = await doFetch(refreshed);
    }
    return res;
  }

  async function me() {
    const token = await getToken();
    if (!token) return null;
    const res = await authedFetch("/auth/me");
    if (!res.ok) return null;
    return res.json();
  }

  async function fetchComps({ community, bedrooms, limit = 10 }) {
    const base = await getBackendUrl();
    const qs = new URLSearchParams();
    if (community) qs.set("community", community);
    if (bedrooms !== undefined && bedrooms !== "") qs.set("bedrooms", String(bedrooms));
    qs.set("limit", String(limit));
    const res = await fetch(`${base}/comps?${qs.toString()}`);
    if (!res.ok) throw new Error(`Comps search failed (${res.status})`);
    return res.json();
  }

  async function submitDealQuery(rawQuery) {
    const token = await getToken();
    if (!token) throw new Error("Sign in first to run a full deal check.");
    const res = await authedFetch("/deals/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_query: rawQuery }),
    });
    if (res.status === 401) {
      await clearToken();
      throw new Error("Session expired -- sign in again.");
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Deal query failed (${res.status})`);
    }
    const data = await res.json();
    return data.query_id;
  }

  function dealUrl(base, queryId) {
    // The extension links out to the real web app's Deal Result page
    // instead of reimplementing the streaming trace UI in a 320px popup.
    // Assumes the frontend is reachable at the backend's own origin with
    // port 3000 in local dev; production deployments should point this at
    // their real Vercel URL via a small edit here.
    const frontendGuess = base.includes("localhost") ? "http://localhost:3000" : base.replace(/^https?:\/\//, "https://");
    return `${frontendGuess}/deals/${queryId}`;
  }

  return {
    DEFAULT_BACKEND_URL,
    getBackendUrl,
    setBackendUrl,
    getToken,
    getRefreshToken,
    setTokens,
    refreshAccessToken,
    clearToken,
    login,
    me,
    fetchComps,
    submitDealQuery,
    dealUrl,
  };
})();
