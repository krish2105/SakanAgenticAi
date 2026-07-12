import Link from "next/link";
import { ThemeToggle } from "@/components/theme-toggle";
import { AuthStatus } from "@/components/auth-status";
import { TransactionTicker } from "@/components/transaction-ticker";
import type { Tick } from "@/lib/types";

export function SiteHeader({ ticks }: { ticks: Tick[] }) {
  return (
    <div className="sticky top-0 z-30 bg-bg">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="font-display text-xl font-semibold tracking-tight text-text-primary">
            Sakan AI
          </span>
          <span className="hidden font-mono text-[10px] uppercase tracking-widest text-text-muted sm:inline">
            deal intelligence terminal
          </span>
        </Link>
        <div className="flex items-center gap-3">
          <AuthStatus />
          <ThemeToggle />
        </div>
      </header>
      <TransactionTicker ticks={ticks} />
    </div>
  );
}
