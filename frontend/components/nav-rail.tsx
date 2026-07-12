"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutGrid, Map, BarChart3, CreditCard } from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { href: "/", label: "Command Deck", icon: LayoutGrid },
  { href: "/comps", label: "Comps Explorer", icon: Map },
  { href: "/market", label: "Analytics", icon: BarChart3 },
  { href: "/billing", label: "Billing", icon: CreditCard },
];

export function NavRail() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Primary"
      className="hidden md:flex w-14 shrink-0 flex-col items-center gap-1 border-r border-border bg-surface py-4"
    >
      {items.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-label={label}
            aria-current={active ? "page" : undefined}
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
