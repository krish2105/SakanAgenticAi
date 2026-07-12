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

  async function setToken(token) {
    await chrome.storage.local.set({ [TOKEN_KEY]: token });
  }

  async function clearToken() {
    await chrome.storage.local.remove(TOKEN_KEY);
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
    await setToken(data.access_token);
    return data.access_token;
  }

  async function me() {
    const token = await getToken();
    if (!token) return null;
    const base = await getBackendUrl();
    const res = await fetch(`${base}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
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
    const base = await getBackendUrl();
    const res = await fetch(`${base}/deals/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
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
    setToken,
    clearToken,
    login,
    me,
    fetchComps,
    submitDealQuery,
    dealUrl,
  };
})();
