import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

describe("hubspot (portal/form id unset)", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_HUBSPOT_PORTAL_ID", "");
    vi.stubEnv("NEXT_PUBLIC_HUBSPOT_FORM_ID", "");
  });
  afterEach(() => vi.unstubAllEnvs());

  it("isHubspotConfigured is false and submit is a no-op", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const hubspot = await import("./hubspot");
    expect(hubspot.isHubspotConfigured()).toBe(false);

    const ok = await hubspot.submitContactSalesLead({ email: "a@b.com" });
    expect(ok).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("hubspot (portal/form id set)", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_HUBSPOT_PORTAL_ID", "12345");
    vi.stubEnv("NEXT_PUBLIC_HUBSPOT_FORM_ID", "abc-form-id");
  });
  afterEach(() => vi.unstubAllEnvs());

  it("isHubspotConfigured is true", async () => {
    const hubspot = await import("./hubspot");
    expect(hubspot.isHubspotConfigured()).toBe(true);
  });

  it("posts to the HubSpot submissions endpoint with the portal/form id and fields", async () => {
    let capturedBody = "";
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      capturedBody = String(init?.body ?? "");
      return { ok: true } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    const hubspot = await import("./hubspot");
    const ok = await hubspot.submitContactSalesLead({
      email: "a@b.com",
      firstname: "Jane",
      company: "Acme",
    });

    expect(ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.hsforms.com/submissions/v3/integration/submit/12345/abc-form-id",
      expect.objectContaining({ method: "POST" })
    );
    expect(JSON.parse(capturedBody).fields).toEqual([
      { name: "email", value: "a@b.com" },
      { name: "firstname", value: "Jane" },
      { name: "company", value: "Acme" },
    ]);
  });

  it("returns false (not throw) when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false }) as Response));
    const hubspot = await import("./hubspot");
    const ok = await hubspot.submitContactSalesLead({ email: "a@b.com" });
    expect(ok).toBe(false);
  });

  it("returns false (not throw) on a network error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );
    const hubspot = await import("./hubspot");
    const ok = await hubspot.submitContactSalesLead({ email: "a@b.com" });
    expect(ok).toBe(false);
  });
});
