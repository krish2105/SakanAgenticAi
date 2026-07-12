# Legal review process

Phase D of the MVP roadmap: "a named legal/compliance partner... a
RERA-licensed firm's name attached to the corpus is the difference between
'AI guessed' and 'reviewed by counsel,' which is what an enterprise buyer
needs to hear." This document is the checklist for that engagement when it
happens — it is not a record that one has happened. As of today, every
document in this directory has `review_status: unreviewed` in its
frontmatter, and the Compliance Agent surfaces an `unreviewed_regulatory_corpus`
flag on every answer as long as that's true (see `app/agents/compliance_agent.py`).

## Why this can't be faked

Every regulatory document in this directory is **synthetic** — styled
after real RERA/DLD form structures (Form A/B/F, escrow rules, Oqood,
title transfer) but not copied from, or verified against, the actual
current regulations. No text in this repo should be treated as legal
advice, and no engagement described below has happened yet. See the root
README's "Ethics & limitations" section.

## What "reviewed" means, per clause

A clause only gets `review_status: reviewed` once all of the following are
true:

1. A RERA-licensed lawyer or firm has read the clause's `text` against the
   actual current regulation it claims to describe (not the synthetic
   version — the real Dubai Land Department / RERA source).
2. Any inaccuracy is either corrected in the clause text or the clause is
   removed/flagged `pending_review` instead of shipped as reviewed.
3. The firm is willing to be named: `reviewed_by` is set to the firm's
   actual name, not "a lawyer" or a placeholder.
4. `review_date` is set to the date of that review — clauses go stale as
   regulations change, and a reviewed clause more than ~12 months old
   should be treated as `pending_review` again until re-confirmed (this
   repo doesn't automate that expiry; track it manually until it does).

## Doing the review

For each of the 12 documents in this directory:

1. Firm reads `<doc>.md` clause-by-clause against the real regulation.
2. For each clause, the firm records: accurate as-is / needs correction /
   not applicable to real regulation (flag for removal).
3. Corrections get applied to the clause `text` directly — this is a
   content fix, not a metadata-only change.
4. Once every clause in a document has been read and is either accurate or
   corrected, update that document's frontmatter:
   ```yaml
   review_status: reviewed
   reviewed_by: <Firm Name>
   review_date: <YYYY-MM-DD>
   ```
5. Re-run the ingestion so the review status actually reaches retrieval,
   not just the source file:
   ```bash
   cd backend
   python scripts/ingest_regulations.py --regulations-dir ../regulations --qdrant-url <your-qdrant-url>
   ```
6. Confirm it worked: a Compliance Agent run that retrieves only clauses
   from a reviewed document should no longer carry the
   `unreviewed_regulatory_corpus` flag (see
   `app.agents.compliance_agent._corpus_review_flag` — it clears the moment
   *any* retrieved clause is `reviewed`, and per-clause review status is
   available in `DealState.retrieved_clauses[].review_status` for a UI
   that wants to distinguish reviewed from unreviewed clauses within one
   answer, which this repo's UI does not currently do).

## What this repo does NOT do

- Re-review on a schedule. `review_date` is recorded but nothing expires
  it automatically — that's a process commitment for whoever owns the
  corpus, not a cron job (contrast with the *content* re-ingestion
  schedule in `.github/workflows/reingest-corpus.yml`, which just keeps
  Qdrant in sync with whatever `review_status` is currently in this
  directory, reviewed or not).
- Track partial review within a single clause. Review status is per
  clause, not per sentence.
- Cover the memo's LLM-generated prose. `review_status` is about the
  underlying regulatory *clause*; the Memo Agent's summary of it is still
  LLM output layered on top, same as everywhere else in this pipeline.
