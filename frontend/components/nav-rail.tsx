"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutGrid, Map, BarChart3, CreditCard } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLocale } from "@/components/locale-provider";

const items = [
  { href: "/", labelKey: "nav.commandDeck", icon: LayoutGrid },
  { href: "/comps", labelKey: "nav.comps", icon: Map },
  { href: "/market", labelKey: "nav.analytics", icon: BarChart3 },
  { href: "/billing", labelKey: "nav.billing", icon: CreditCard },
];

export function NavRail() {
  const pathname = usePathname();
  const { t } = useLocale();

  return (
    <nav
      aria-label="Primary"
      className="hidden md:flex w-14 shrink-0 flex-col items-center gap-1 border-e border-border bg-surface py-4"
    >
      {items.map(({ href, labelKey, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        const label = t(labelKey);
        return (
          <Link
            key={href}
            href={href}
            aria-label={label}
            aria-current={active ? "page" : undefined}
            title={label}
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brass",
              active
                ? "bg-brass/15 text-brass"
                : "text-text-muted hover:bg-border/40 hover:text-text-primary"
            )}
          >
            <Icon size={18} />
          </Link>
        );
      })}
    </nav>
  );
}
