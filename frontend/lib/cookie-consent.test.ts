import { describe, it, expect, beforeEach } from "vitest";
import { getCookieConsent, setCookieConsent } from "./cookie-consent";

describe("cookie-consent", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("returns null when no choice has been made yet", () => {
    expect(getCookieConsent()).toBeNull();
  });

  it("persists an accepted choice", () => {
    setCookieConsent("accepted");
    expect(getCookieConsent()).toBe("accepted");
  });

  it("persists a rejected choice", () => {
    setCookieConsent("rejected");
    expect(getCookieConsent()).toBe("rejected");
  });

  it("ignores an unrelated or corrupted localStorage value", () => {
    window.localStorage.setItem("sakan_cookie_consent", "yes-please");
    expect(getCookieConsent()).toBeNull();
  });
});
