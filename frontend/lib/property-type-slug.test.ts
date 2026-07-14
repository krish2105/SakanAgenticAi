import { describe, it, expect } from "vitest";
import { propertyTypeToSlug } from "./property-type-slug";

describe("propertyTypeToSlug", () => {
  it("lowercases a single word", () => {
    expect(propertyTypeToSlug("Apartment")).toBe("apartment");
  });

  it("hyphenates multi-word types", () => {
    expect(propertyTypeToSlug("Off Plan Villa")).toBe("off-plan-villa");
  });

  it("collapses non-alphanumeric separators", () => {
    expect(propertyTypeToSlug("Townhouse/Villa")).toBe("townhouse-villa");
  });

  it("trims surrounding whitespace", () => {
    expect(propertyTypeToSlug("  Penthouse  ")).toBe("penthouse");
  });
});
