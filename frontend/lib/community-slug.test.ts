import { describe, it, expect } from "vitest";
import { communityToSlug } from "./community-slug";

describe("communityToSlug", () => {
  it("lowercases and hyphenates multi-word names", () => {
    expect(communityToSlug("Dubai Marina")).toBe("dubai-marina");
    expect(communityToSlug("Jumeirah Village Circle")).toBe("jumeirah-village-circle");
  });

  it("lowercases an all-caps acronym instead of leaving it untouched", () => {
    // Regression: a naive reverse (title-case each slug word) would have
    // turned "damac-hills" back into "Damac Hills", not "DAMAC Hills" --
    // this is exactly why there's no slugToCommunity() in this module;
    // resolution has to go forward against the real community list instead.
    expect(communityToSlug("DAMAC Hills")).toBe("damac-hills");
  });

  it("trims surrounding whitespace", () => {
    expect(communityToSlug("  Al Barari  ")).toBe("al-barari");
  });
});
