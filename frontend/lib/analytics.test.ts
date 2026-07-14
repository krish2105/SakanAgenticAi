import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const posthogMock = {
  init: vi.fn(),
  capture: vi.fn(),
  identify: vi.fn(),
  reset: vi.fn(),
};

vi.mock("posthog-js", () => ({ default: posthogMock }));

describe("analytics (NEXT_PUBLIC_POSTHOG_KEY unset)", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "");
    Object.values(posthogMock).forEach((fn) => fn.mockClear());
  });
  afterEach(() => vi.unstubAllEnvs());

  it("every export is a no-op without a key configured", async () => {
    const analytics = await import("./analytics");
    analytics.initAnalytics();
    analytics.capture("some_event", { a: 1 });
    analytics.capturePageview("/deals");
    analytics.identifyUser(1, { email: "a@b.com" });
    analytics.resetAnalytics();

    expect(posthogMock.init).not.toHaveBeenCalled();
    expect(posthogMock.capture).not.toHaveBeenCalled();
    expect(posthogMock.identify).not.toHaveBeenCalled();
    expect(posthogMock.reset).not.toHaveBeenCalled();
  });
});

describe("analytics (NEXT_PUBLIC_POSTHOG_KEY set, consent not yet accepted)", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test_key");
    window.localStorage.clear();
    Object.values(posthogMock).forEach((fn) => fn.mockClear());
  });
  afterEach(() => vi.unstubAllEnvs());

  it("every export stays a no-op until the visitor accepts the cookie banner", async () => {
    const analytics = await import("./analytics");
    analytics.initAnalytics();
    analytics.capture("some_event");
    analytics.capturePageview("/deals");
    analytics.identifyUser(1);

    expect(posthogMock.init).not.toHaveBeenCalled();
    expect(posthogMock.capture).not.toHaveBeenCalled();
    expect(posthogMock.identify).not.toHaveBeenCalled();
  });
});

describe("analytics (NEXT_PUBLIC_POSTHOG_KEY set, consent accepted)", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test_key");
    window.localStorage.setItem("sakan_cookie_consent", "accepted");
    Object.values(posthogMock).forEach((fn) => fn.mockClear());
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    window.localStorage.clear();
  });

  it("initAnalytics initializes posthog-js exactly once", async () => {
    const analytics = await import("./analytics");
    analytics.initAnalytics();
    analytics.initAnalytics(); // second call should be a no-op guard
    expect(posthogMock.init).toHaveBeenCalledTimes(1);
    expect(posthogMock.init).toHaveBeenCalledWith("phc_test_key", expect.objectContaining({ capture_pageview: false }));
  });

  it("capture forwards the event name and properties", async () => {
    const analytics = await import("./analytics");
    analytics.capture("deal_query_submitted", { query_length: 42 });
    expect(posthogMock.capture).toHaveBeenCalledWith("deal_query_submitted", { query_length: 42 });
  });

  it("capturePageview sends a $pageview event with the url", async () => {
    const analytics = await import("./analytics");
    analytics.capturePageview("/deals/9");
    expect(posthogMock.capture).toHaveBeenCalledWith("$pageview", { $current_url: "/deals/9" });
  });

  it("identifyUser stringifies numeric ids", async () => {
    const analytics = await import("./analytics");
    analytics.identifyUser(9, { role: "user" });
    expect(posthogMock.identify).toHaveBeenCalledWith("9", { role: "user" });
  });

  it("resetAnalytics calls posthog.reset", async () => {
    const analytics = await import("./analytics");
    analytics.resetAnalytics();
    expect(posthogMock.reset).toHaveBeenCalledTimes(1);
  });
});
