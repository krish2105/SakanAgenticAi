import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import {
  setTokens,
  getAccessToken,
  getRefreshToken,
  clearTokens,
  onTokenChange,
  loginUser,
  fetchDeals,
  retryDealQuery,
  fetchAdminStats,
  fetchAdminUsers,
  setAdminUserTier,
  fetchAdminQueryVolume,
  AuthRequiredError,
} from "@/lib/api";

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("token storage", () => {
  beforeEach(() => clearTokens());

  it("stores and reads access + refresh tokens", () => {
    setTokens("access-1", "refresh-1");
    expect(getAccessToken()).toBe("access-1");
    expect(getRefreshToken()).toBe("refresh-1");
  });

  it("clearTokens removes both", () => {
    setTokens("a", "r");
    clearTokens();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("notifies subscribers on change", () => {
    const seen: (string | null)[] = [];
    const unsub = onTokenChange((t) => seen.push(t));
    setTokens("access-2", "refresh-2");
    clearTokens();
    unsub();
    setTokens("ignored"); // after unsubscribe
    expect(seen).toEqual(["access-2", null]);
  });
});

describe("loginUser", () => {
  beforeEach(() => clearTokens());
  afterEach(() => vi.restoreAllMocks());

  it("stores both tokens from the login response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(200, { access_token: "acc", refresh_token: "ref" }))
    );
    await loginUser("a@b.com", "pw");
    expect(getAccessToken()).toBe("acc");
    expect(getRefreshToken()).toBe("ref");
  });
});

describe("silent refresh on 401", () => {
  beforeEach(() => clearTokens());
  afterEach(() => vi.restoreAllMocks());

  it("refreshes and retries once, then returns data", async () => {
    setTokens("expired-access", "good-refresh");

    const fetchMock = vi.fn(async (url: string) => {
      if (url.includes("/auth/refresh")) {
        return jsonResponse(200, { access_token: "fresh-access", refresh_token: "fresh-refresh" });
      }
      if (url.includes("/deals")) {
        // First call (expired token) -> 401; after refresh -> 200.
        return getAccessToken() === "fresh-access"
          ? jsonResponse(200, { deals: [{ query_id: 1, raw_query: "x", status: "complete" }] })
          : jsonResponse(401, { detail: "expired" });
      }
      return jsonResponse(404, {});
    });
    vi.stubGlobal("fetch", fetchMock);

    const deals = await fetchDeals("expired-access");
    expect(deals).toHaveLength(1);
    expect(getAccessToken()).toBe("fresh-access");
    // Original 401 + refresh + retry = 3 fetches.
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("throws AuthRequiredError when the refresh token is also invalid", async () => {
    setTokens("expired-access", "dead-refresh");

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.includes("/auth/refresh")) return jsonResponse(401, { detail: "nope" });
        return jsonResponse(401, { detail: "expired" });
      })
    );

    await expect(fetchDeals("expired-access")).rejects.toBeInstanceOf(AuthRequiredError);
    // A failed refresh clears stored tokens.
    expect(getAccessToken()).toBeNull();
  });
});

describe("retryDealQuery", () => {
  beforeEach(() => clearTokens());
  afterEach(() => vi.restoreAllMocks());

  it("posts to the retry endpoint and returns the query id", async () => {
    setTokens("access-1");
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toContain("/deals/42/retry");
      expect(init?.method).toBe("POST");
      return jsonResponse(202, { query_id: "42" });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await retryDealQuery("42", "access-1");
    expect(result.query_id).toBe("42");
  });

  it("surfaces the 409 message when the deal isn't in a retryable state", async () => {
    setTokens("access-1");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(409, { detail: "Only a failed deal query can be retried (current status: done)." })
      )
    );

    await expect(retryDealQuery("42", "access-1")).rejects.toThrow(/current status: done/);
  });
});

describe("admin API functions", () => {
  beforeEach(() => clearTokens());
  afterEach(() => vi.restoreAllMocks());

  it("fetchAdminStats GETs /admin/stats", async () => {
    setTokens("access-1");
    const fetchMock = vi.fn(async (url: string) => {
      expect(url).toContain("/admin/stats");
      return jsonResponse(200, { total_users: 5, verified_users: 2, total_deals: 10, users_by_tier: {} });
    });
    vi.stubGlobal("fetch", fetchMock);

    const stats = await fetchAdminStats("access-1");
    expect(stats.total_users).toBe(5);
  });

  it("fetchAdminUsers forwards q/limit/offset as query params", async () => {
    setTokens("access-1");
    const fetchMock = vi.fn(async (url: string) => {
      expect(url).toContain("/admin/users?");
      expect(url).toContain("q=alice");
      expect(url).toContain("limit=25");
      expect(url).toContain("offset=0");
      return jsonResponse(200, { total: 1, limit: 25, offset: 0, users: [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    const page = await fetchAdminUsers("access-1", { q: "alice" });
    expect(page.total).toBe(1);
  });

  it("setAdminUserTier PATCHes the tier endpoint", async () => {
    setTokens("access-1");
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toContain("/admin/users/7/tier");
      expect(init?.method).toBe("PATCH");
      expect(init?.body).toBe(JSON.stringify({ tier: "pro" }));
      return jsonResponse(200, { user_id: 7, tier: "pro" });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await setAdminUserTier(7, "pro", "access-1");
    expect(result).toEqual({ user_id: 7, tier: "pro" });
  });

  it("setAdminUserTier surfaces a 400 for an unknown tier", async () => {
    setTokens("access-1");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(400, { detail: "Unknown tier 'diamond'. Valid: ['enterprise', ...]" }))
    );

    await expect(setAdminUserTier(7, "diamond", "access-1")).rejects.toThrow(/Unknown tier/);
  });

  it("fetchAdminQueryVolume GETs /admin/query-volume with days param", async () => {
    setTokens("access-1");
    const fetchMock = vi.fn(async (url: string) => {
      expect(url).toContain("/admin/query-volume?days=30");
      return jsonResponse(200, [{ day: "2026-07-01", count: 3 }]);
    });
    vi.stubGlobal("fetch", fetchMock);

    const volume = await fetchAdminQueryVolume("access-1", 30);
    expect(volume).toEqual([{ day: "2026-07-01", count: 3 }]);
  });
});
