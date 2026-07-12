"use client";

import { useEffect } from "react";

/** Catches errors in the root layout itself (where the normal error.tsx can't
 * reach). Must render its own <html>/<body>. Deliberately minimal and
 * self-contained so it works even if the app's providers/styles failed. */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0B1220",
          color: "#EDEFF3",
          fontFamily: "system-ui, sans-serif",
          padding: "1.5rem",
        }}
      >
        <div style={{ maxWidth: 420, textAlign: "center" }}>
          <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>Sakan AI hit a fatal error</h1>
          <p style={{ color: "#8A94AC", marginBottom: "1.5rem" }}>
            Something went wrong while loading the app. Please try again.
          </p>
          <button
            onClick={() => reset()}
            style={{
              background: "#C9A227",
              color: "#0B1220",
              border: "none",
              borderRadius: 8,
              padding: "0.6rem 1.25rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
