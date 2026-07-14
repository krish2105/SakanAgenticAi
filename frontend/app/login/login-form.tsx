"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";
import { useLocale } from "@/components/locale-provider";
import { TurnstileWidget } from "@/components/turnstile-widget";

export function LoginForm() {
  const { login, register } = useAuth();
  const { t } = useLocale();
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") || "/";

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password, turnstileToken || undefined);
      } else {
        await register(email, password, fullName || undefined, turnstileToken || undefined);
      }
      router.push(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-6 py-12">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">{t("app.title")}</p>
      <h1 className="mt-2 font-display text-2xl font-semibold text-text-primary">
        {mode === "login" ? t("auth.signIn") : t("auth.createYourAccount")}
      </h1>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">
            {mode === "login" ? t("auth.welcomeBack") : t("auth.getStarted")}
          </CardTitle>
          <CardDescription>
            {mode === "login" ? t("auth.signInDescription") : t("auth.registerDescription")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            {mode === "register" && (
              <Input
                placeholder={t("auth.fullNameOptional")}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
              />
            )}
            <Input
              type="email"
              placeholder={t("auth.emailPlaceholder")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
            <Input
              type="password"
              placeholder={t("auth.password")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={mode === "register" ? 8 : undefined}
              required
            />
            <TurnstileWidget onVerify={setTurnstileToken} />
            {error && <p className="text-sm text-negative">{error}</p>}
            <Button type="submit" disabled={submitting} className="mt-1">
              {submitting ? t("auth.pleaseWait") : mode === "login" ? t("auth.signIn") : t("auth.createAccount")}
            </Button>
          </form>
          {mode === "login" && (
            <Link
              href="/forgot"
              className="mt-3 block text-center text-sm text-text-muted underline decoration-dotted hover:text-text-primary"
            >
              {t("auth.forgotPassword")}
            </Link>
          )}
        </CardContent>
      </Card>

      <button
        onClick={() => {
          setMode(mode === "login" ? "register" : "login");
          setError(null);
        }}
        className="mt-4 text-center text-sm text-text-muted underline decoration-dotted hover:text-text-primary"
      >
        {mode === "login" ? t("auth.needAccount") : t("auth.haveAccount")}
      </button>
    </div>
  );
}
