"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useLocale } from "@/components/locale-provider";
import { NAV_ITEMS, isActive } from "@/lib/nav-items";

/** Bottom tab bar for phones. The desktop NavRail is `hidden md:flex`, so
 * without this there was no primary navigation at all under the md breakpoint.
 * Fixed to the bottom, safe-area aware. */
export function MobileNav() {
  const pathname = usePathname();
  const { t } = useLocale();

  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-3 bottom-[calc(0.75rem+env(safe-area-inset-bottom))] z-40 flex rounded-2xl border border-border bg-surface/85 shadow-lg shadow-black/10 backdrop-blur-md supports-[backdrop-filter]:bg-surface/70 dark:shadow-black/30 md:hidden"
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
            className={cn(
              "flex flex-1 flex-col items-center gap-1 py-2.5 text-[10px] transition-all duration-200",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brass",
              "first:rounded-s-2xl last:rounded-e-2xl",
              active ? "text-brass" : "text-text-muted hover:text-text-primary"
            )}
          >
            <Icon size={18} />
            <span className="max-w-full truncate">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
