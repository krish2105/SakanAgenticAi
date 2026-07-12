import { Suspense } from "react";
import { ResetForm } from "./reset-form";

export default function ResetPage() {
  return (
    <Suspense fallback={<div className="px-6 py-12 text-sm text-text-muted">Loading…</div>}>
      <ResetForm />
    </Suspense>
  );
}
