import { describe, it, expect } from "vitest";
import { cn, formatAed, formatCompactAed } from "@/lib/utils";

describe("cn", () => {
  it("merges and dedupes tailwind classes", () => {
    expect(cn("p-2", "p-4")).toBe("p-4"); // later wins
    expect(cn("text-sm", false && "hidden", "font-bold")).toBe("text-sm font-bold");
  });
});

describe("formatAed", () => {
  it("rounds and groups thousands", () => {
    expect(formatAed(1850000)).toBe("AED 1,850,000");
    expect(formatAed(1234.6)).toBe("AED 1,235");
  });
});

describe("formatCompactAed", () => {
  it("uses M/K suffixes", () => {
    expect(formatCompactAed(2_500_000)).toBe("AED 2.50M");
    expect(formatCompactAed(750_000)).toBe("AED 750K");
    expect(formatCompactAed(500)).toBe("AED 500");
  });
});
