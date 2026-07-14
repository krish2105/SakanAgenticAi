import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginForm } from "./login-form";

export const metadata: Metadata = {
  title: "Sign in",
  robots: { index: false },
};

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="px-6 py-12 text-sm text-text-muted">Loading…</div>}>
      <LoginForm />
    </Suspense>
  );
}
