import type { Metadata } from "next";
import { LegalDraftBanner } from "@/components/legal-draft-banner";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "Sakan AI's Privacy Policy (draft, pending legal review).",
  robots: { index: false },
};

const LAST_UPDATED = "13 July 2026";

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">Legal</p>
      <h1 className="mt-1 font-display text-3xl font-semibold text-text-primary">Privacy Policy</h1>
      <p className="mt-1 text-sm text-text-muted">Last updated: {LAST_UPDATED}</p>

      <div className="mt-6">
        <LegalDraftBanner />
      </div>

      <div className="prose prose-sm mt-8 max-w-none dark:prose-invert prose-headings:font-display prose-a:text-brass">
        <h2>1. What we collect</h2>
        <ul>
          <li>
            <strong>Account data:</strong> email address, password (stored as a salted bcrypt
            hash, never in plain text), and optionally your name and role.
          </li>
          <li>
            <strong>Query content:</strong> the natural-language deal questions you submit, and
            the resulting comps, valuation, compliance, and memo output tied to your account.
          </li>
          <li>
            <strong>Usage &amp; security data:</strong> login timestamps, failed-login counts (for
            account-lockout protection), and request logs tagged with a correlation ID for
            debugging — logs do not include full query content.
          </li>
          <li>
            <strong>Billing data:</strong> handled by our payment processor; we store a customer
            reference ID, not your card details.
          </li>
        </ul>

        <h2>2. How we use it</h2>
        <p>
          To operate the service (run your queries, authenticate you, enforce plan quotas), to
          secure accounts (lockouts, session/refresh-token management), to improve the product
          (aggregate, de-identified quality evaluation of agent outputs), and to communicate
          service-related notices (password reset, email verification, billing).
        </p>

        <h2>3. Retention and deletion</h2>
        <p>
          Deal queries and their results are retained for a limited window (180 days by default)
          and then automatically purged by a scheduled job, along with their associated audit-log
          entries. You can request earlier deletion of your account and associated data by
          contacting us.
        </p>

        <h2>4. Where your data lives</h2>
        <p>
          Application data is stored with our managed database and vector-search providers.
          Authentication tokens are stored in your browser&apos;s local storage, not third-party
          cookies. See our{" "}
          <a href="/legal/dpa">Data Processing Addendum</a> for the current list of
          infrastructure sub-processors.
        </p>

        <h2>5. Third parties</h2>
        <p>
          We use a small number of infrastructure providers to run Sakan (hosting, database,
          vector search, payments, and — for enabled channels only — email delivery and WhatsApp
          messaging). We do not sell your personal data.
        </p>

        <h2>6. Your rights</h2>
        <p>
          Depending on your jurisdiction, you may have rights to access, correct, export, or
          delete your personal data. Contact us to exercise these rights; we aim to respond within
          30 days.
        </p>

        <h2>7. Contact</h2>
        <p>
          Privacy questions or requests: <a href="mailto:privacy@sakan.ai">privacy@sakan.ai</a>.
        </p>
      </div>
    </div>
  );
}
