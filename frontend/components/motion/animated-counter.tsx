"use client";

import { useEffect, useRef } from "react";
import { useInView, useMotionValue, useSpring } from "framer-motion";
import { cn } from "@/lib/utils";

/** Counts up from 0 to `value` once it scrolls into view, spring-eased. */
export function AnimatedCounter({
  value,
  className,
  prefix = "",
  suffix = "",
  decimals = 0,
}: {
  value: number;
  className?: string;
  prefix?: string;
  suffix?: string;
  decimals?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.6 });
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { stiffness: 90, damping: 24 });

  useEffect(() => {
    if (isInView) motionValue.set(value);
  }, [isInView, value, motionValue]);

  useEffect(
    () =>
      spring.on("change", (latest) => {
        if (ref.current) {
          const formatted = latest.toLocaleString("en-US", {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
          });
          ref.current.textContent = `${prefix}${formatted}${suffix}`;
        }
      }),
    [spring, prefix, suffix, decimals]
  );

  return (
    <span ref={ref} className={cn("font-mono-nums", className)}>
      {prefix}
      {(0).toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {suffix}
    </span>
  );
}
