import { LayoutGrid, Map, BarChart3, FileText, Bookmark, CreditCard, type LucideIcon } from "lucide-react";

export interface NavItem {
  href: string;
  labelKey: string;
  icon: LucideIcon;
}

/** Single source of truth for primary navigation, shared by the desktop
 * NavRail and the mobile bottom bar so they never drift apart. */
export const NAV_ITEMS: NavItem[] = [
  { href: "/", labelKey: "nav.commandDeck", icon: LayoutGrid },
  { href: "/comps", labelKey: "nav.comps", icon: Map },
  { href: "/market", labelKey: "nav.analytics", icon: BarChart3 },
  { href: "/deals", labelKey: "nav.deals", icon: FileText },
  { href: "/saved", labelKey: "nav.saved", icon: Bookmark },
  { href: "/billing", labelKey: "nav.billing", icon: CreditCard },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}
