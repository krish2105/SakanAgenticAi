import * as React from "react";
import { cn } from "@/lib/utils";

/** A shimmering placeholder block. Respects prefers-reduced-motion via the
 * animate-pulse utility (Tailwind disables it under reduced-motion). */
export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-border/60", className)}
      aria-hidden="true"
      {...props}
    />
  );
}
