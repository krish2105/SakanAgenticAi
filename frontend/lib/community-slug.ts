/** One-directional: community name -> URL slug. There is deliberately no
 * slugToCommunity() -- naively title-casing a slug back can't recover an
 * all-caps acronym like "DAMAC" ("damac-hills" -> "Damac Hills" is wrong).
 * Callers must resolve a slug back to a real community name by fetching
 * the actual list (e.g. fetchMarketSnapshot()) and matching
 * communityToSlug(candidate) === slug -- see app/guides/[community]/page.tsx. */
export function communityToSlug(community: string): string {
  return community.trim().toLowerCase().replace(/\s+/g, "-");
}
