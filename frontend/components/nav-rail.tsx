"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useLocale } from "@/components/locale-provider";
import { NAV_ITEMS, isActive } from "@/lib/nav-items";

export function NavRail() {
  const pathname = usePathname();
  const { t } = useLocale();

  return (
    <nav
      aria-label="Primary"
      className={cn(
        "sticky top-20 hidden h-fit w-16 shrink-0 flex-col items-center gap-1.5 self-start ms-3",
        "rounded-2xl border border-border bg-surface/70 py-4 shadow-lg shadow-black/[0.03]",
        "backdrop-blur-md supports-[backdrop-filter]:bg-surface/60 md:flex",
        "dark:shadow-black/20"
      )}
    >
      {NAV_ITEMS.map(({ href, labelKey, icon: Icon }) => {
        const active = isActive(pathname, href);
        const label = t(labelKey);
        return (
          <Link
            key={href}
            href={href}
            aria-label={label}
            aria-current={active ? "page" : undefined}
            title={label}
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-xl transition-all duration-200",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brass",
              active
                ? "bg-brass/15 text-brass shadow-[inset_0_0_0_1px_rgba(166,130,30,0.25)]"
                : "text-text-muted hover:-translate-y-0.5 hover:bg-border/40 hover:text-text-primary"
            )}
          >
            <Icon size={18} />
          </Link>
        );
      })}
    </nav>
  );
}
