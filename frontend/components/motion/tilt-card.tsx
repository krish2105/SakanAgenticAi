"use client";

import { useRef } from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { cn } from "@/lib/utils";

/**
 * Mouse-driven 3D tilt: the card leans away from the cursor on a
 * `rotateX`/`rotateY` CSS transform, spring-damped back to flat on
 * pointer-leave. Disabled under prefers-reduced-motion by CSS (the
 * transform still applies but springs are near-instant there via the
 * global reduced-motion rule in globals.css).
 */
export function TiltCard({
  children,
  className,
  glare = true,
  style,
  wrapperClassName,
}: {
  children: React.ReactNode;
  className?: string;
  glare?: boolean;
  style?: React.CSSProperties;
  /** Applied to the outer perspective wrapper -- use for float/entrance
   * animations that also touch `transform`, so they don't fight the
   * inner element's mouse-tilt transform (both animate the same property). */
  wrapperClassName?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const rotateX = useMotionValue(0);
  const rotateY = useMotionValue(0);
  const springX = useSpring(rotateX, { stiffness: 200, damping: 20 });
  const springY = useSpring(rotateY, { stiffness: 200, damping: 20 });
  const glareX = useTransform(springY, [-8, 8], [0, 100]);
  const glareY = useTransform(springX, [8, -8], [0, 100]);
  const glareBackground = useTransform(
    [glareX, glareY],
    ([gx, gy]: number[]) => `radial-gradient(circle at ${gx}% ${gy}%, rgb(var(--accent-brass) / 0.14), transparent 60%)`
  );

  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    rotateY.set((px - 0.5) * 16);
    rotateX.set((0.5 - py) * 16);
  }

  function handleMouseLeave() {
    rotateX.set(0);
    rotateY.set(0);
  }

  return (
    <div className={cn("perspective-1200", wrapperClassName)} style={style}>
      <motion.div
        ref={ref}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{ rotateX: springX, rotateY: springY }}
        className={cn("group preserve-3d relative overflow-hidden rounded-xl", className)}
      >
        {children}
        {glare && (
          <motion.div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
            style={{ background: glareBackground }}
          />
        )}
      </motion.div>
    </div>
  );
}
