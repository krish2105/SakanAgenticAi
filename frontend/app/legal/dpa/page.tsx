import type { Metadata } from "next";
import { LegalDraftBanner } from "@/components/legal-draft-banner";

export const metadata: Metadata = {
  title: "Data Processing Addendum",
  description: "Sakan AI's Data Processing Addendum (draft, pending legal review).",
  robots: { index: false },
};

const LAST_UPDATED = "13 July 2026";

const SUB_PROCESSORS = [
  { name: "Render", purpose: "Application hosting (API)" },
  { name: "Vercel", purpose: "Application hosting (frontend)" },
  { name: "Neon", purpose: "Primary database (Postgres)" },
  { name: "Qdrant Cloud", purpose: "Vector search for regulatory-clause retrieval" },
  { name: "Stripe", purpose: "Subscription billing and payment processing" },
  { name: "Anthropic", purpose: "LLM reasoning (only when configured with an API key)" },
  { name: "Meta (WhatsApp Business Platform)", purpose: "Optional WhatsApp query channel, when enabled" },
  { name: "Sentry", purpose: "Optional error tracking, when enabled" },
];

export default function DpaPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">Legal</p>
      <h1 className="mt-1 font-display text-3xl font-semibold text-text-primary">
        Data Processing Addendum
      </h1>
      <p className="mt-1 text-sm text-text-muted">Last updated: {LAST_UPDATED}</p>

      <div className="mt-6">
        <LegalDraftBanner />
      </div>

      <div className="prose prose-sm mt-8 max-w-none dark:prose-invert prose-headings:font-display prose-a:text-brass">
        <h2>1. Scope</h2>
        <p>
          This addendum describes how Sakan AI processes personal data on behalf of a customer
          (the &ldquo;controller&rdquo;) when Sakan acts as a data &ldquo;processor&rdquo; — for
          example, an organization&apos;s agents submitting deal queries containing client
          contact details. It supplements our Terms of Service and Privacy Policy.
        </p>

        <h2>2. Nature and purpose of processing</h2>
        <p>
          Sakan processes the content of submitted queries and the resulting agent outputs solely
          to provide the deal-intelligence service: retrieving comparable transactions, computing
          a valuation, checking regulatory compliance signals, and generating a memo. Data is not
          used to train models on customer content beyond aggregate, de-identified quality
          evaluation of the agent pipeline itself.
        </p>

        <h2>3. Sub-processors</h2>
        <p>
          We use the following categories of infrastructure sub-processor. Not every deployment
          enables every optional integration (LLM reasoning, WhatsApp, error tracking) — see your
          deployment&apos;s configuration for what is actually active.
        </p>
        <table>
          <thead>
            <tr>
              <th>Sub-processor</th>
              <th>Purpose</th>
            </tr>
          </thead>
          <tbody>
            {SUB_PROCESSORS.map((sp) => (
              <tr key={sp.name}>
                <td>{sp.name}</td>
                <td>{sp.purpose}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <h2>4. Security measures</h2>
        <ul>
          <li>Passwords are hashed with bcrypt; they are never stored or logged in plain text.</li>
          <li>
            Authentication uses short-lived access tokens plus rotating refresh tokens (stored as
            SHA-256 hashes, not plaintext), with account lockout after repeated failed logins.
          </li>
          <li>
            All administrative and billing-webhook endpoints require verified, signed requests in
            production; the service refuses to start if required signing secrets are missing.
          </li>
          <li>Data in transit is encrypted via TLS.</li>
        </ul>

        <h2>5. Data retention and deletion</h2>
        <p>
          Deal-query records (and their audit-log entries) are automatically purged after a
          configurable retention window (180 days by default) by a scheduled job. Controllers may
          request earlier deletion by contacting us.
        </p>

        <h2>6. International transfers</h2>
        <p>
          Sub-processors may process data outside your home jurisdiction. Each sub-processor
          maintains its own data-protection commitments; details are available on request.
        </p>

        <h2>7. Contact</h2>
        <p>
          DPA and sub-processor questions: <a href="mailto:privacy@sakan.ai">privacy@sakan.ai</a>.
        </p>
      </div>
    </div>
  );
}
