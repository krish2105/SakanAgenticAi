import type { Metadata } from "next";
import { LegalDraftBanner } from "@/components/legal-draft-banner";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "Sakan AI's Terms of Service (draft, pending legal review).",
  robots: { index: false },
};

const LAST_UPDATED = "13 July 2026";

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <p className="font-mono text-xs uppercase tracking-widest text-brass">Legal</p>
      <h1 className="mt-1 font-display text-3xl font-semibold text-text-primary">Terms of Service</h1>
      <p className="mt-1 text-sm text-text-muted">Last updated: {LAST_UPDATED}</p>

      <div className="mt-6">
        <LegalDraftBanner />
      </div>

      <div className="prose prose-sm mt-8 max-w-none dark:prose-invert prose-headings:font-display prose-a:text-brass">
        <h2>1. What Sakan AI is</h2>
        <p>
          Sakan AI (&ldquo;Sakan&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;) is a deal-intelligence
          tool for Dubai real estate. Given a plain-English query, it retrieves comparable
          transactions, computes a valuation range, checks the query against a regulatory corpus
          for RERA-related compliance signals, and produces a memo. Every claim in a Sakan output
          is designed to cite its source (a specific comparable transaction or a specific
          regulatory clause).
        </p>

        <h2>2. Not legal, financial, or valuation advice</h2>
        <p>
          Sakan is a research and drafting aid, not a substitute for a licensed valuer, a lawyer,
          or a RERA-registered compliance professional. Valuation ranges are a statistical
          estimate from a limited comparable set, not a certified appraisal. Compliance summaries
          are drawn from a regulatory corpus that, unless explicitly marked otherwise on a given
          clause, has <strong>not been reviewed by licensed counsel</strong> (see our{" "}
          <a href="/legal/dpa">Data Processing Addendum</a> and the compliance disclaimer shown
          on every deal result). You are responsible for independent verification before making
          any transaction, investment, or compliance decision.
        </p>

        <h2>3. Accounts and acceptable use</h2>
        <ul>
          <li>You must provide accurate registration information and keep your credentials secure.</li>
          <li>
            You may not use Sakan to scrape, resell, or bulk-export data beyond your plan&apos;s
            stated limits, or to build a competing product from our outputs.
          </li>
          <li>
            We may suspend accounts that abuse rate limits, attempt to circumvent quota
            enforcement, or violate applicable law.
          </li>
        </ul>

        <h2>4. Data sources</h2>
        <p>
          Depending on configuration, transaction data displayed may be synthetic demonstration
          data, a public open-data mirror of DLD transaction records, or (once available) a
          licensed data partnership feed. Every transaction record carries a provenance tag; see
          our documentation for the current data-source configuration of any given deployment.
        </p>

        <h2>5. Subscriptions and billing</h2>
        <p>
          Paid plans are billed monthly in advance via our payment processor. You can cancel at
          any time; access continues until the end of the current billing period. Fees are
          non-refundable except where required by law.
        </p>

        <h2>6. Disclaimers and limitation of liability</h2>
        <p>
          Sakan is provided &ldquo;as is&rdquo; without warranties of any kind. To the maximum
          extent permitted by law, we are not liable for indirect, incidental, or consequential
          damages, or for decisions made in reliance on Sakan&apos;s outputs without independent
          verification.
        </p>

        <h2>7. Changes</h2>
        <p>
          We may update these Terms as the product evolves. Material changes will be reflected by
          updating the &ldquo;Last updated&rdquo; date above.
        </p>

        <h2>8. Contact</h2>
        <p>
          Questions about these Terms: <a href="mailto:legal@sakan.ai">legal@sakan.ai</a>.
        </p>
      </div>
    </div>
  );
}
