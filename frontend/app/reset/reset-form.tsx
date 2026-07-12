"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { resetPassword } from "@/lib/api";

export function ResetForm() {
  const router = useRouter();
  const token = useSearchParams().get("token") || "";
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await resetPassword(token, password);
      setDone(true);
      setTimeout(() => router.push("/login"), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-6 py-12">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">Sakan AI</p>
      <h1 className="mt-2 font-display text-2xl font-semibold text-text-primary">Set a new password</h1>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Choose a new password</CardTitle>
          <CardDescription>At least 8 characters. This signs out your other sessions.</CardDescription>
        </CardHeader>
        <CardContent>
          {!token ? (
            <p className="text-sm text-negative">
              This reset link is missing its token. Request a new one from the sign-in page.
            </p>
          ) : done ? (
            <p className="text-sm text-positive">Password updated. Redirecting you to sign in…</p>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
              <Input
                type="password"
                placeholder="New password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                minLength={8}
                required
              />
              {error && <p className="text-sm text-negative">{error}</p>}
              <Button type="submit" disabled={submitting} className="mt-1">
                {submitting ? "Updating…" : "Update password"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>

      <Link
        href="/login"
        className="mt-4 text-center text-sm text-text-muted underline decoration-dotted hover:text-text-primary"
      >
        Back to sign in
      </Link>
    </div>
  );
}
