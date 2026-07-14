/** Same one-directional pattern as community-slug.ts: forward-match a slug
 * against the live property-type list rather than reverse-title-casing it.
 * Property type names ("Apartment", "Off-Plan Villa") don't carry the
 * acronym ambiguity community names do (see community-slug.ts's DAMAC
 * regression test), but keeping both slug helpers structurally identical
 * means there's exactly one pattern to reason about across the guides
 * section, not two. */
export function propertyTypeToSlug(propertyType: string): string {
  return propertyType
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
