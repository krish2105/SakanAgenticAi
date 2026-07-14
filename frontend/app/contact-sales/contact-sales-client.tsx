"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { isHubspotConfigured, submitContactSalesLead } from "@/lib/hubspot";

const SALES_EMAIL = "sales@sakan.ai";

function mailtoFallback(fields: { firstname: string; email: string; company: string; message: string }) {
  const subject = "Sakan AI Enterprise";
  const body = [
    fields.message,
    "",
    `Name: ${fields.firstname || "—"}`,
    `Company: ${fields.company || "—"}`,
    `Email: ${fields.email}`,
  ].join("\n");
  window.location.href = `mailto:${SALES_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

export function ContactSalesClient() {
  const [firstname, setFirstname] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [mailtoOpened, setMailtoOpened] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (isHubspotConfigured()) {
        const ok = await submitContactSalesLead({ email, firstname: firstname || undefined, company: company || undefined, message: message || undefined });
        if (!ok) throw new Error("submission failed");
        setSent(true);
      } else {
        // No CRM configured -- fall back to opening the visitor's mail
        // client with the message prefilled, rather than losing it. Can't
        // confirm the mail client actually opened, so this doesn't claim
        // "sent" the way the HubSpot path does.
        mailtoFallback({ firstname, email, company, message });
        setMailtoOpened(true);
      }
    } catch {
      setError(`Something went wrong. Email us directly at ${SALES_EMAIL}.`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-6 py-12">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">Enterprise</p>
      <h1 className="mt-2 font-display text-2xl font-semibold text-text-primary">Contact sales</h1>
      <p className="mt-3 text-text-muted">
        Team plans, licensed data feeds, or custom compliance review — tell us what you need and
        we&apos;ll follow up.
      </p>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">
            {sent ? "Thanks — we'll be in touch" : mailtoOpened ? "Almost there" : "Get in touch"}
          </CardTitle>
          {!sent && !mailtoOpened && <CardDescription>Usually a reply within one business day.</CardDescription>}
          {mailtoOpened && (
            <CardDescription>
              Your email client should have opened with this pre-filled. If nothing happened, email{" "}
              <a href={`mailto:${SALES_EMAIL}`} className="text-brass underline">
                {SALES_EMAIL}
              </a>{" "}
              directly.
            </CardDescription>
          )}
        </CardHeader>
        {!sent && !mailtoOpened && (
          <CardContent>
            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
              <Input
                placeholder="Name"
                value={firstname}
                onChange={(e) => setFirstname(e.target.value)}
                autoComplete="name"
              />
              <Input
                type="email"
                placeholder="Work email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
              <Input
                placeholder="Company (optional)"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                autoComplete="organization"
              />
              <textarea
                placeholder="What are you looking for?"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={4}
                className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brass"
              />
              {error && <p className="text-sm text-negative">{error}</p>}
              <Button type="submit" disabled={submitting} className="mt-1">
                {submitting ? "Sending…" : "Send"}
              </Button>
            </form>
          </CardContent>
        )}
      </Card>

      <p className="mt-4 text-center text-sm text-text-muted">
        Prefer email? Reach us directly at{" "}
        <a href={`mailto:${SALES_EMAIL}`} className="text-brass underline">
          {SALES_EMAIL}
        </a>
        .
      </p>
    </div>
  );
}
