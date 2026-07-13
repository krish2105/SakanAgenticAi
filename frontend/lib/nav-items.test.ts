import { describe, it, expect } from "vitest";
import { NAV_ITEMS, isActive } from "@/lib/nav-items";

describe("NAV_ITEMS", () => {
  it("includes the deal-history route", () => {
    expect(NAV_ITEMS.some((i) => i.href === "/deals")).toBe(true);
  });
  it("every item has a stable href + label key", () => {
    for (const item of NAV_ITEMS) {
      expect(item.href.startsWith("/")).toBe(true);
      expect(item.labelKey.startsWith("nav.")).toBe(true);
    }
  });
});

describe("isActive", () => {
  it("matches the home route exactly (not as a prefix)", () => {
    expect(isActive("/", "/")).toBe(true);
    expect(isActive("/comps", "/")).toBe(false);
  });
  it("matches non-home routes by prefix", () => {
    expect(isActive("/deals/42", "/deals")).toBe(true);
    expect(isActive("/market", "/market")).toBe(true);
    expect(isActive("/comps", "/market")).toBe(false);
  });
});
