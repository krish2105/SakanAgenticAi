"use client";

import { Bookmark } from "lucide-react";
import { cn } from "@/lib/utils";

/** Presentational only -- the parent owns the saved-IDs set and the
 * save/unsave API calls, since a comps list needs to know "which of these
 * are saved" as a batch (one fetch), not have each row independently ask. */
export function SaveCompButton({
  saved,
  onToggle,
  className,
}: {
  saved: boolean;
  onToggle: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
      aria-label={saved ? "Remove from watchlist" : "Save to watchlist"}
      aria-pressed={saved}
      className={cn(
        "rounded p-1 transition-colors hover:bg-border/40",
        saved ? "text-brass" : "text-text-muted hover:text-text-primary",
        className
      )}
    >
      <Bookmark size={15} className={saved ? "fill-current" : undefined} />
    </button>
  );
}
