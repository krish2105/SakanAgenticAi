import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import {
  setTokens,
  getAccessToken,
  getRefreshToken,
  clearTokens,
  onTokenChange,
  loginUser,
  startDemoSession,
  fetchDeals,
  retryDealQuery,
  createMemoShareLink,
  revokeMemoShareLink,
  fetchSharedMemo,
  fetchAdminStats,
  fetchAdminUsers,
  setAdminUserTier,
  fetchAdminQueryVolume,
  inviteTeamMember,
  acceptTeamInvite,
  fetchTeamMembers,
  removeTeamMember,
  fetchReadiness,
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

  it("reports a 404 as a misconfiguration, not a credential error", async () => {
    // A bare 404 from /auth/login never means "wrong password" -- the route
    // always exists -- it means the request was misrouted (e.g. a trailing
    // slash in NEXT_PUBLIC_API_URL producing a double-slash path). FastAPI's
    // default 404 body ({"detail":"Not Found"}) must not surface verbatim,
    // since it reads exactly like a real auth error to an end user.
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(404, { detail: "Not Found" })));
    await expect(loginUser("a@b.com", "pw")).rejects.toThrow(/misconfigured/i);
  });
});

describe("startDemoSession", () => {
  beforeEach(() => clearTokens());
  afterEach(() => vi.restoreAllMocks());

  it("POSTs to /auth/demo with no body and stores the returned tokens", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toContain("/auth/demo");
      expect(init?.method).toBe("POST");
      expect(init?.body).toBeUndefined();
      return jsonResponse(201, { access_token: "demo-acc", refresh_token: "demo-ref" });
    });
    vi.stubGlobal("fetch", fetchMock);

    await startDemoSession();
    expect(getAccessToken()).toBe("demo-acc");
    expect(getRefreshToken()).toBe("demo-ref");
  });

  it("throws when the backend rejects the demo request", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(429, { detail: "Too many requests" })));
    await expect(startDemoSession()).rejects.toThrow();
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

describe("shareable memo links", () => {
  beforeEach(() => clearTokens());
  afterEach(() => vi.restoreAllMocks());

  it("createMemoShareLink POSTs and returns the share URL", async () => {
    setTokens("access-1");
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toContain("/deals/42/share");
      expect(init?.method).toBe("POST");
      return jsonResponse(200, { share_token: "abc123", share_url: "https://sakan.example/memo/abc123" });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createMemoShareLink("42", "access-1");
    expect(result.share_url).toBe("https://sakan.example/memo/abc123");
  });

  it("createMemoShareLink surfaces a 409 when the memo isn't generated yet", async () => {
    setTokens("access-1");
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(409, { detail: "Memo not yet generated for this deal" })));
    await expect(createMemoShareLink("42", "access-1")).rejects.toThrow(/not yet generated/);
  });

  it("revokeMemoShareLink DELETEs the share link", async () => {
    setTokens("access-1");
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toContain("/deals/42/share");
      expect(init?.method).toBe("DELETE");
      return { ok: false, status: 204, json: async () => ({}) } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(revokeMemoShareLink("42", "access-1")).resolves.toBeUndefined();
  });

  it("fetchSharedMemo needs no auth token and returns the memo on success", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toContain("/deals/shared/abc123");
      expect(init?.headers).toBeUndefined();
      return jsonResponse(200, {
        memo_markdown: "# Memo",
        raw_query: "2BR Dubai Marina",
        created_at: "2026-01-01T00:00:00",
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const memo = await fetchSharedMemo("abc123");
    expect(memo?.memo_markdown).toBe("# Memo");
  });

  it("fetchSharedMemo returns null for a revoked or unknown token", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(404, { detail: "This share link is invalid or has been revoked" })));
    expect(await fetchSharedMemo("gone")).toBeNull();
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

describe("team billing API functions", () => {
  beforeEach(() => clearTokens());
  afterEach(() => vi.restoreAllMocks());

  it("inviteTeamMember POSTs the invitee email", async () => {
    setTokens("access-1");
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toContain("/billing/team/invite");
      expect(init?.method).toBe("POST");
      expect(init?.body).toBe(JSON.stringify({ email: "teammate@example.com" }));
      return jsonResponse(200, { invited_user_id: 9 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await inviteTeamMember("teammate@example.com", "access-1");
    expect(result.invited_user_id).toBe(9);
  });

  it("inviteTeamMember surfaces a 404 when the invitee has no account", async () => {
    setTokens("access-1");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(404, { detail: "No Sakan AI account with that email yet -- ask them to register first" })
      )
    );

    await expect(inviteTeamMember("nobody@example.com", "access-1")).rejects.toThrow(/register first/);
  });

  it("acceptTeamInvite POSTs the raw token", async () => {
    setTokens("access-1");
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toContain("/billing/team/accept");
      expect(init?.body).toBe(JSON.stringify({ token: "raw-invite-token" }));
      return jsonResponse(200, { organization_id: 1, seat_count: 2 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await acceptTeamInvite("raw-invite-token", "access-1");
    expect(result.seat_count).toBe(2);
  });

  it("fetchTeamMembers returns the roster when the caller is on a team", async () => {
    setTokens("access-1");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(200, [{ user_id: 1, email: "owner@example.com", full_name: null, is_owner: true }])
      )
    );

    const members = await fetchTeamMembers("access-1");
    expect(members).toHaveLength(1);
    expect(members?.[0].is_owner).toBe(true);
  });

  it("fetchTeamMembers returns null (not throw) for a non-team user", async () => {
    setTokens("access-1");
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(404, { detail: "You're not on a team." })));

    const members = await fetchTeamMembers("access-1");
    expect(members).toBeNull();
  });

  it("removeTeamMember DELETEs the member endpoint", async () => {
    setTokens("access-1");
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toContain("/billing/team/members/7");
      expect(init?.method).toBe("DELETE");
      return jsonResponse(200, { removed_user_id: 7, seat_count: 1 });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(removeTeamMember(7, "access-1")).resolves.toBeUndefined();
  });
});

describe("fetchReadiness", () => {
  it("treats a 503 (not ready) response as real data, not a fetch failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(503, { ready: false, checks: { database: { ok: false, detail: "error: timeout" } } })
      )
    );

    const report = await fetchReadiness();
    expect(report).toEqual({
      reachable: true,
      ready: false,
      checks: { database: { ok: false, detail: "error: timeout" } },
    });
  });

  it("reports reachable: false only on a genuine network failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const report = await fetchReadiness();
    expect(report).toEqual({ reachable: false, ready: false, checks: {} });
  });
});

describe("API_BASE", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("strips a trailing slash so requests never end up with a double slash", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com/");
    vi.resetModules();
    const { API_BASE } = await import("@/lib/api");
    expect(API_BASE).toBe("https://api.example.com");
  });

  it("leaves a URL with no trailing slash unchanged", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com");
    vi.resetModules();
    const { API_BASE } = await import("@/lib/api");
    expect(API_BASE).toBe("https://api.example.com");
  });
});
