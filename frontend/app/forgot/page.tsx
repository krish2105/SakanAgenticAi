"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { requestPasswordReset } from "@/lib/api";

export default function ForgotPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await requestPasswordReset(email);
      setSubmitted(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-6 py-12">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">Sakan AI</p>
      <h1 className="mt-2 font-display text-2xl font-semibold text-text-primary">Reset your password</h1>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Forgot password</CardTitle>
          <CardDescription>
            Enter your email and we&apos;ll send you a link to set a new password.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {submitted ? (
            <p className="text-sm text-text-primary">
              If that email is registered, a reset link is on its way. Check your inbox.
            </p>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
              <Input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
              <Button type="submit" disabled={submitting} className="mt-1">
                {submitting ? "Sending…" : "Send reset link"}
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
