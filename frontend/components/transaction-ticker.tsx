"use client";
import { motion, useReducedMotion } from "framer-motion";
import type { Tick } from "@/lib/types";

export function TransactionTicker({ ticks }: { ticks: Tick[] }) {
  const shouldReduceMotion = useReducedMotion();

  if (ticks.length === 0) return null;

  return (
    <div className="w-full overflow-hidden border-y border-border bg-surface py-1.5">
      <motion.div
        className="flex gap-8 whitespace-nowrap font-mono text-xs text-text-muted will-change-transform"
        animate={shouldReduceMotion ? undefined : { x: ["0%", "-50%"] }}
        transition={{ duration: 40, ease: "linear", repeat: Infinity }}
      >
        {[...ticks, ...ticks].map((t, i) => (
          <span key={i}>
            <span className="text-text-primary">{t.building}</span>
            {" · "}
            {t.community} · {t.beds}BR ·{" "}
            <span className="text-brass">AED {t.price.toLocaleString()}</span>
            {" · "}
            {t.type}
          </span>
        ))}
      </motion.div>
    </div>
  );
}
