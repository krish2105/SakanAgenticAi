import { cn } from "@/lib/utils";

/**
 * Ambient drifting gradient blobs behind a hero section. Pure CSS
 * (keyframes in globals.css) so it renders on the server and costs nothing
 * client-side; disabled entirely under prefers-reduced-motion.
 */
export function AuroraBackground({ className }: { className?: string }) {
  return (
    <div className={cn("pointer-events-none absolute inset-0 -z-10 overflow-hidden", className)} aria-hidden="true">
      <div
        className="animate-aurora-a absolute -left-1/4 -top-1/4 h-[60%] w-[60%] rounded-full opacity-40 blur-3xl"
        style={{
          background:
            "radial-gradient(circle, rgb(var(--accent-brass) / 0.55), transparent 70%)",
        }}
      />
      <div
        className="animate-aurora-b absolute -right-1/4 top-0 h-[55%] w-[55%] rounded-full opacity-30 blur-3xl"
        style={{
          background: "radial-gradient(circle, rgb(var(--positive) / 0.4), transparent 70%)",
        }}
      />
      <div
        className="animate-aurora-a absolute bottom-[-20%] left-1/3 h-[50%] w-[50%] rounded-full opacity-20 blur-3xl"
        style={{
          background: "radial-gradient(circle, rgb(var(--negative) / 0.35), transparent 70%)",
          animationDelay: "-8s",
        }}
      />
    </div>
  );
}
