"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

/** Route-segment error boundary. Catches render/data errors in the app shell
 * and offers a recovery path instead of a white screen. */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surfaced to the browser console; Sentry (if wired on the frontend later)
    // would capture here too.
    console.error("Route error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6">
      <div className="max-w-md text-center">
        <p className="font-mono text-xs uppercase tracking-wider text-text-muted">Something went wrong</p>
        <h1 className="mt-2 font-display text-2xl font-semibold text-text-primary">
          This page hit an unexpected error
        </h1>
        <p className="mt-2 text-sm text-text-muted">
          The issue has been logged. You can try again, or head back to the command deck.
        </p>
        {error.digest && (
          <p className="mt-2 font-mono text-xs text-text-muted">Reference: {error.digest}</p>
        )}
        <div className="mt-6 flex items-center justify-center gap-3">
          <Button onClick={() => reset()}>Try again</Button>
          <Button variant="outline" onClick={() => (window.location.href = "/")}>
            Go home
          </Button>
        </div>
      </div>
    </div>
  );
}
