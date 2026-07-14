"use client";

import { Search } from "lucide-react";

/** Decoupled from CommandPalette on purpose -- a custom event instead of
 * shared context, since this button and the palette itself don't otherwise
 * need to know about each other. */
export function CommandPaletteTrigger() {
  return (
    <button
      type="button"
      onClick={() => window.dispatchEvent(new Event("sakan:open-command-palette"))}
      className="hidden items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text-muted transition-colors hover:border-brass hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brass sm:flex"
      aria-label="Open command palette"
    >
      <Search size={13} />
      <span className="font-body">Search</span>
      <kbd className="rounded border border-border px-1 font-mono text-[10px]">⌘K</kbd>
    </button>
  );
}
