import type { Metadata } from "next";
import Link from "next/link";
import { Reveal, RevealGroup, RevealItem } from "@/components/motion/reveal";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://sakan-agentic-ai.vercel.app";

export const metadata: Metadata = {
  title: "Investor FAQ",
  description:
    "Common questions about Sakan AI's data sources, valuation methodology, and compliance checks for Dubai real estate deal intelligence.",
  alternates: { canonical: `${SITE_URL}/faq` },
};

const FAQS: { question: string; answer: string }[] = [
  {
    question: "Where do the comparable transactions come from?",
    answer:
      "Every comp is tagged with its actual source, shown right on the row: synthetic demo data, the public DLD/Kaggle open dataset, the free DLD open-data API, or a licensed partner feed once one exists. Nothing is presented as a real transaction unless it is one — see the Comps Explorer's Source column.",
  },
  {
    question: "How is the valuation range calculated?",
    answer:
      "A statistical model (AVM) derived from the comps actually retrieved for your query — the interquartile range (P25–P75) of comparable prices, padded to account for a small sample. It's a defensible estimate grounded in real comps, not an LLM guess; the exact method used for a given query is shown on its Valuation card.",
  },
  {
    question: "Is the compliance check a substitute for legal advice?",
    answer:
      "No. The Compliance Agent retrieves and cites specific clauses from a RERA regulatory corpus, but that corpus has not been reviewed by licensed counsel unless a clause explicitly says otherwise. When nothing relevant is found, or the corpus hasn't been reviewed, Sakan says \"unable to verify\" rather than guessing — see our Terms of Service for the full disclaimer.",
  },
  {
    question: "What happens if a valuation or compliance check can't be completed?",
    answer:
      "Every agent has an explicit fallback: if the LLM is unavailable, it degrades to a deterministic heuristic (comps ranking, AVM stats, or a documented \"unable to verify\") instead of failing silently or fabricating an answer. Every claim in the output is designed to trace back to a specific comp or clause.",
  },
  {
    question: "How much does it cost?",
    answer:
      "Starter is free — 5 full-pipeline queries a month, unlimited comps search. Pro (AED 299/mo) raises that to 50. Team (AED 999/mo) is unmetered. Enterprise is custom, with API access and a dedicated compliance corpus. See the Pricing page for the current breakdown.",
  },
  {
    question: "Can I use this data outside the app?",
    answer:
      "Comps can be exported as CSV from the Comps Explorer or any deal result, and a partner API key (from your account page) gives programmatic read-only access to the same comps data, rate-limited per key.",
  },
  {
    question: "Is my data private?",
    answer:
      "Deal queries and their results are scoped to your account — another user can't read your deals by guessing an ID. See the Privacy Policy and Data Processing Addendum for the full data-handling and retention policy.",
  },
];

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: FAQS.map((f) => ({
    "@type": "Question",
    name: f.question,
    acceptedAnswer: { "@type": "Answer", text: f.answer },
  })),
};

export default function FaqPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <Reveal>
        <p className="font-mono text-xs uppercase tracking-widest text-brass">FAQ</p>
        <h1 className="mt-1 font-display text-3xl font-semibold text-text-primary">Investor FAQ</h1>
        <p className="mt-2 max-w-2xl text-sm text-text-muted">
          What Sakan AI&apos;s data, valuations, and compliance checks actually are — and aren&apos;t.
        </p>
      </Reveal>

      <RevealGroup className="mt-8 flex flex-col gap-6">
        {FAQS.map((f) => (
          <RevealItem key={f.question}>
            <div className="border-b border-border pb-6 last:border-0">
              <h2 className="font-display text-base font-semibold text-text-primary">{f.question}</h2>
              <p className="mt-2 text-sm leading-relaxed text-text-muted">{f.answer}</p>
            </div>
          </RevealItem>
        ))}
      </RevealGroup>

      <p className="mt-8 text-xs text-text-muted">
        More questions?{" "}
        <Link href="/contact-sales" className="text-brass underline">
          Contact us
        </Link>
        .
      </p>
    </div>
  );
}
