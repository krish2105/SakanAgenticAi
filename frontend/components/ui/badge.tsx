import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[11px] font-medium",
  {
    variants: {
      variant: {
        default: "border-brass/40 bg-brass/10 text-brass",
        // Solid fill, not a tinted background -- a tinted positive/negative
        // chip failed WCAG AA color-contrast in an axe-core audit (Phase 21)
        // at this badge's 11px size. White text clears 4.5:1 against the
        // light-theme token but not the brighter dark-theme one; dark ink
        // does the reverse -- hence the dark: override, verified with
        // axe-core in both themes, not just computed by hand.
        positive: "border-transparent bg-positive text-white dark:text-[#0A1615]",
        negative: "border-transparent bg-negative text-white dark:text-[#0A1615]",
        muted: "border-border bg-surface-raised text-text-muted",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
