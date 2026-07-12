import { Suspense } from "react";
import { VerifyClient } from "./verify-client";

export default function VerifyPage() {
  return (
    <Suspense fallback={<div className="px-6 py-12 text-sm text-text-muted">Loading…</div>}>
      <VerifyClient />
    </Suspense>
  );
}
