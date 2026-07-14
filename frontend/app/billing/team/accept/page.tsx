import { Suspense } from "react";
import type { Metadata } from "next";
import { AcceptInviteClient } from "./accept-client";

export const metadata: Metadata = {
  title: "Accept team invite — Sakan AI",
  robots: { index: false, follow: false },
};

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={<div className="px-6 py-12 text-sm text-text-muted">Loading…</div>}>
      <AcceptInviteClient />
    </Suspense>
  );
}
