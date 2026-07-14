# Sakan AI — Master Prompt & Architecture Document
### Agentic Real Estate Deal Intelligence Platform (Dubai / DLD)

**Prepared for:** Krishna Mathur — MAIB, SP Jain Dubai (AS25DXB018)
**Purpose:** Hand this document to an agentic coding tool (Claude Code) as the single source of truth to build Sakan AI end-to-end — agentic pipeline, full RAG, and a distinctive, modern light/dark UI.
**Status:** Portfolio / recruiter-facing project. Entirely synthetic transaction data, modeled on real DLD/RERA structures. Not affiliated with, or claiming data from, the actual Dubai Land Department.

*"Sakan" (سكن) — Arabic for dwelling/residence.*

---

## 0. HOW TO USE THIS DOCUMENT (instructions to the coding agent)

Build in the phase order in Section 12. Section 4 is a completed design brainstorm — do not re-derive the palette or type system, implement it exactly as specified, including the dark/light theme tokens. Every agent must be independently testable before you wire them into the LangGraph pipeline. Do not use placeholder Lorem Ipsum copy anywhere in the UI — use real Dubai community names, real-sounding building names, and AED figures consistent with the synthetic dataset in Section 7. Ask no clarifying questions; business decisions are pre-made in Section 13.

---

## 1. PROBLEM STATEMENT

Dubai Land Department recorded **AED 252 billion in real estate transactions in Q1 2026 alone, across 60,303 transactions** — one of the largest, most data-rich property markets in the world, moving toward machine-readable records under the state's own agentic-AI push. Yet the sector's actual AI investment has gone almost entirely into faster outbound marketing: AI cold-callers, AI-generated listings, WhatsApp lead-scoring bots. The workflows where agentic AI should compound fastest — **pricing, comps, underwriting, due diligence, investor reporting, lease abstraction, market memos** — remain manual, and the dominant broker workflow is still built around a static PDF brochure and a WhatsApp voice note.

At the same time, the market has real structural complexity an agent needs to reason over correctly:
- **Off-plan dominates** — roughly 72% of residential activity in 2025-26 — which means every deal touches developer payment-plan structures, escrow account rules, and Oqood pre-registration, not just a simple title transfer.
- **RERA compliance is non-trivial** — Form A (developer registration), Form B (unit reservation), Form F (sale & purchase agreement) each carry distinct requirements, and RERA's updated 2026 guidelines specifically require disclosure when property descriptions or marketing images are AI-generated — a compliance detail most AI real-estate tools ignore entirely.
- **The market is genuinely multilingual and international** — Dubai buyers span English, Arabic, Russian, Hindi and Chinese-speaking segments, and over 60% of the population speaks Arabic day-to-day.

**The gap:** existing tools (PropertyGPT, BayutGPT, HayyAI) are conversational *search* interfaces — good at "show me listings." None of them are agentic *deal-intelligence* tools that autonomously pull comps, compute a defensible valuation, check RERA compliance for a specific unit or off-plan project, and hand a broker or investor a cited, ready-to-send memo.

**Target user:** a Dubai real-estate agent, brokerage analyst, or individual investor who needs a fast, defensible answer to "what is this deal actually worth, and is it clean?" — not another listings search box.

**Core value proposition:** *"Ask Sakan a deal question in plain English. It pulls real comps, computes a valuation range it can justify, checks the compliance paperwork, and hands you a memo — showing its work at every step."*

---

## 2. SOLUTION OVERVIEW

Sakan AI is a 5-node LangGraph pipeline:

```
Natural-language deal query
      │
      ▼
[1] Query Agent        ──► parses intent + structured filters from free text
      │
      ▼
[2] Comps Agent         ──► retrieves comparable transactions (structured + semantic)
      │
      ▼
[3] Valuation Agent      ──► computes a fair-value range with a stated method
      │
      ▼
[4] Compliance RAG Agent ──► retrieves & cites RERA/DLD rules relevant to this deal
      │
      ▼
[5] Memo Agent           ──► synthesizes everything into a cited, investor-ready memo
      │
      ▼
Live trace + downloadable memo + comps map
```

Every node writes to a shared `DealState` object, streamed live to the frontend's **Deal Intelligence Trace** drawer — the same "show your work" principle as your ClaimGuard project, applied to property instead of claims.

---

## 3. TECH STACK (final decisions — do not deviate)

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui | matches UAE job-spec expectations; production-grade |
| Theming | `next-themes`, class-based Tailwind dark mode, CSS variable tokens | instant light/dark toggle, no flash-of-wrong-theme |
| Animation | Framer Motion | for the ticker, trace drawer, and map marker transitions |
| Maps | Mapbox GL JS (free tier, Dubai district polygons) — fallback: `react-leaflet` + OpenStreetMap if you want zero API cost | comps need to be seen geographically, not just tabulated |
| Charts | Recharts | market trend lines, price-per-sqft by district |
| Backend | FastAPI (Python 3.11) | async, pairs cleanly with LangGraph |
| Agent orchestration | **LangGraph** | stateful, controllable, inspectable multi-agent workflow |
| LLM | Claude API — Sonnet for Valuation/Compliance/Memo reasoning, Haiku for Query parsing | cost-controlled, quality where it matters |
| Vector DB | **Qdrant** (Docker, self-hosted) | free, real vector-DB experience, matches job-spec keywords |
| Embeddings | Gemini `gemini-embedding-001` (free API, default once `GEMINI_API_KEY` is set) — fallback: `sentence-transformers/all-MiniLM-L6-v2` (local, free, RAM-heavy) | no API cost dependency either way; see `app/embeddings.py` |
| Structured DB | PostgreSQL 15 via SQLAlchemy + Alembic | transactions, buildings, developers, projects |
| Auth | Simple role selector (Agent / Investor / Admin) — no full auth system | keep scope on the agentic/RAG/UI core |
| Deployment | Frontend → Vercel, Backend + Postgres + Qdrant → Docker Compose on Railway/Render | live demo link, not just a repo |

---

## 4. DESIGN SYSTEM (completed brainstorm — implement exactly as specified)

### 4.1 Grounding

Subject: a **deal-intelligence terminal** for Dubai property — closer to a trading desk tool than a consumer listings site. Audience: brokers and analysts who live in dense data all day. The page's single job: make a firehose of transaction data feel instantly legible and trustworthy, in both light and dark conditions (agents work this at a desk in daylight and on-site on a phone at dusk).

### 4.2 Self-critique against generic AI-design defaults

Ruled out on purpose: (1) warm cream + terracotta — the most common AI-generated default, and Dubai real-estate marketing sites already overuse a "sandy/warm" palette, so it would read as templated rather than intentional; (2) near-black + single neon accent — too consumer-startup, undersells the "regulated financial instrument" feel this tool needs; (3) broadsheet hairline-rule newspaper layout — wrong metaphor for a live data terminal. Instead: a **terminal-meets-Arabian-modernism** direction — deep Gulf-night navy paired with a muted brass accent (the material language of Dubai's own towers — brass detailing, gold signage — reinterpreted as a data-precision color, not a luxury cliché).

### 4.3 Token system

**Color — Dark mode (default):**
| Token | Hex | Use |
|---|---|---|
| `--bg` | `#0B1220` | app background, deep Gulf-night navy |
| `--surface` | `#121B2E` | cards, panels |
| `--surface-raised` | `#182338` | modals, drawers |
| `--border` | `#25324A` | hairlines, dividers |
| `--text-primary` | `#EDEFF3` | headings, key data |
| `--text-muted` | `#8A94AC` | labels, captions |
| `--accent-brass` | `#C9A227` | primary CTA, live-data highlights, active states |
| `--accent-brass-dim` | `#8C7420` | hover/pressed states |
| `--positive` | `#2F9E68` | value-up, approved, compliant |
| `--negative` | `#C4573B` | value-down, flagged, non-compliant |

**Color — Light mode:**
| Token | Hex | Use |
|---|---|---|
| `--bg` | `#F3F5F8` | cool paper — deliberately NOT warm cream, to avoid the generic AI-design tell |
| `--surface` | `#FFFFFF` | cards, panels |
| `--surface-raised` | `#FFFFFF` with `shadow-md` | modals, drawers |
| `--border` | `#D8DEE8` | hairlines |
| `--text-primary` | `#101828` | headings |
| `--text-muted` | `#5B6478` | labels |
| `--accent-brass` | `#A6821E` | same hue family, darkened for light-background contrast |
| `--positive` | `#1F7A4D` | |
| `--negative` | `#A8432B` | |

**Typography:**
- Display: **Fraunces** (variable, weight 500–650, slight optical sizing) — a warm, characterful serif for section headers and the hero query prompt. Used with restraint — headlines only, never body text.
- Body: **IBM Plex Sans** — clean, professional, has genuine Arabic-script support if you extend to bilingual later, which most default sans stacks don't.
- Data/utility: **IBM Plex Mono** — every AED figure, price-per-sqft, transaction ID, and timestamp renders in this face. This is deliberate: numbers reading in monospace is what makes the interface feel like an instrument rather than a brochure.

**Layout concept:** a "command deck" — persistent left icon-rail for section nav, a full-width **Transaction Ticker** strip pinned under the header, and a main canvas that splits into query/results on the left two-thirds and a slide-in **Agent Trace drawer** on the right third when a query is running.

```
┌─────────────────────────────────────────────────────────┐
│ ☰  Sakan AI            [ AED transaction ticker →→→ ]  ◐ │  ← header + ticker + theme toggle
├───┬─────────────────────────────────────┬───────────────┤
│ ▤ │  Query bar: "2BR Business Bay <2M"   │ Agent Trace   │
│ 🗺 │  ┌─────────┐ ┌─────────┐            │ ① Query  ✓    │
│ 📊 │  │ comp     │ │ comp    │  ...        │ ② Comps  ✓    │
│ 📄 │  └─────────┘ └─────────┘            │ ③ Valuation ⋯ │
│   │  Valuation range: AED 1.85M–2.05M    │ ④ Compliance  │
│   │  Compliance: Form F ✓ · Escrow ✓     │ ⑤ Memo        │
└───┴─────────────────────────────────────┴───────────────┘
```

**Signature element:** the **Transaction Ticker** — a thin, continuously-scrolling strip of live-feeling synthetic DLD-style transactions (`Marina Gate II · 2BR · AED 2.1M · Sale`) running under the header at all times. It's the single element that makes the "deal intelligence terminal" thesis land in the first second, and it doubles as ambient proof the dataset is real and moving, not a static mock.

### 4.4 Implementation — theme system

**`tailwind.config.ts`:**
```ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "rgb(var(--bg) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        "surface-raised": "rgb(var(--surface-raised) / <alpha-value>)",
        border: "rgb(var(--border) / <alpha-value>)",
        "text-primary": "rgb(var(--text-primary) / <alpha-value>)",
        "text-muted": "rgb(var(--text-muted) / <alpha-value>)",
        brass: "rgb(var(--accent-brass) / <alpha-value>)",
        "brass-dim": "rgb(var(--accent-brass-dim) / <alpha-value>)",
        positive: "rgb(var(--positive) / <alpha-value>)",
        negative: "rgb(var(--negative) / <alpha-value>)",
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "serif"],
        body: ["var(--font-plex-sans)", "sans-serif"],
        mono: ["var(--font-plex-mono)", "monospace"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
```

**`app/globals.css`:**
```css
:root {
  --bg: 243 245 248;
  --surface: 255 255 255;
  --surface-raised: 255 255 255;
  --border: 216 222 232;
  --text-primary: 16 24 40;
  --text-muted: 91 100 120;
  --accent-brass: 166 130 30;
  --accent-brass-dim: 140 108 20;
  --positive: 31 122 77;
  --negative: 168 67 43;
}

.dark {
  --bg: 11 18 32;
  --surface: 18 27 46;
  --surface-raised: 24 35 56;
  --border: 37 50 74;
  --text-primary: 237 239 243;
  --text-muted: 138 148 172;
  --accent-brass: 201 162 39;
  --accent-brass-dim: 140 116 32;
  --positive: 47 158 104;
  --negative: 196 87 59;
}

body {
  @apply bg-bg text-text-primary font-body transition-colors duration-200;
}
```

**`app/providers.tsx`:**
```tsx
"use client";
import { ThemeProvider } from "next-themes";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
      {children}
    </ThemeProvider>
  );
}
```

**`app/layout.tsx`** must wrap `<body>` with `<Providers>` and set `suppressHydrationWarning` on `<html>` (required by next-themes to avoid hydration flash — do not skip this).

**`components/theme-toggle.tsx`:**
```tsx
"use client";
import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="h-9 w-9" />; // avoid layout shift pre-hydration

  return (
    <button
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      aria-label="Toggle theme"
      className="h-9 w-9 rounded-full border border-border bg-surface
                 flex items-center justify-center transition-colors
                 hover:border-brass focus-visible:outline-none
                 focus-visible:ring-2 focus-visible:ring-brass"
    >
      {theme === "dark" ? (
        <Sun size={16} className="text-brass" />
      ) : (
        <Moon size={16} className="text-brass" />
      )}
    </button>
  );
}
```

### 4.5 Signature component sketch — `components/transaction-ticker.tsx`

```tsx
"use client";
import { motion } from "framer-motion";

type Tick = { building: string; community: string; beds: number; price: number; type: "Sale" | "Off-Plan" | "Mortgage" };

export function TransactionTicker({ ticks }: { ticks: Tick[] }) {
  return (
    <div className="w-full overflow-hidden border-y border-border bg-surface py-1.5">
      <motion.div
        className="flex gap-8 whitespace-nowrap font-mono text-xs text-text-muted"
        animate={{ x: ["0%", "-50%"] }}
        transition={{ duration: 40, ease: "linear", repeat: Infinity }}
      >
        {[...ticks, ...ticks].map((t, i) => (
          <span key={i}>
            <span className="text-text-primary">{t.building}</span>
            {" · "}{t.community} · {t.beds}BR ·{" "}
            <span className="text-brass">AED {t.price.toLocaleString()}</span>
            {" · "}{t.type}
          </span>
        ))}
      </motion.div>
    </div>
  );
}
```

*(Note: `enableSystem` + `respectMotionPreference` — wrap the ticker's `animate` with a `useReducedMotion()` check from Framer Motion so it freezes for users with reduced-motion OS settings, per accessibility floor.)*

---

## 5. MULTI-AGENT ARCHITECTURE — DETAILED SPEC

### 5.1 Shared State Object

```python
from pydantic import BaseModel
from typing import Literal, Optional

class DealState(BaseModel):
    query_id: str
    raw_query: str

    # Query Agent output
    query_type: Optional[Literal["comps_search", "valuation", "compliance_check", "full_memo"]] = None
    community: Optional[str] = None
    property_type: Optional[str] = None       # Apartment | Villa | Townhouse
    bedrooms: Optional[int] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    project_id: Optional[str] = None           # if off-plan and named

    # Comps Agent output
    retrieved_comps: list[dict] = []           # [{transaction_id, building, price, price_per_sqft, date}]

    # Valuation Agent output
    valuation_low: Optional[float] = None
    valuation_high: Optional[float] = None
    valuation_method: Optional[str] = None      # e.g. "comp-median +/- 8%, adjusted for floor/view"
    valuation_rationale: Optional[str] = None

    # Compliance RAG Agent output
    retrieved_clauses: list[dict] = []          # [{clause_id, text, source_doc, similarity}]
    compliance_flags: list[str] = []            # e.g. ["escrow_unverified", "rera_form_f_required"]
    compliance_summary: Optional[str] = None

    # Memo Agent output
    memo_markdown: Optional[str] = None

    agent_trace: list[dict] = []                # append-only, streamed to frontend
```

### 5.2 Agent 1 — Query Agent

**Job:** turn free-text like `"2BR Business Bay under AED 2M, check RERA for the off-plan Marina Gate II project"` into structured `DealState` fields.
**Model:** Claude Haiku (cheap, fast, deterministic extraction).

**System prompt:**
```
You are the Query Agent for Sakan AI, a Dubai real-estate deal-intelligence system.
Extract structured filters from the user's natural-language query. Output ONLY valid JSON:

{
  "query_type": "comps_search" | "valuation" | "compliance_check" | "full_memo",
  "community": string | null,
  "property_type": "Apartment" | "Villa" | "Townhouse" | null,
  "bedrooms": number | null,
  "budget_min": number | null,
  "budget_max": number | null,
  "project_id": string | null
}

Infer query_type "full_memo" if the user asks for a report, memo, or "everything" about a
deal. Infer "compliance_check" if they mention RERA, Form A/B/F, escrow, or legality.
Otherwise default to "comps_search" if no valuation or compliance language is present.

QUERY: {raw_query}
```

### 5.3 Agent 2 — Comps Agent

**Job:** retrieve comparable transactions — hybrid structured filter (community/bedrooms/budget from Postgres) + semantic re-rank (Qdrant, for queries like "similar building quality" that don't map to a column filter).

**Tools:** `structured_comp_query_tool` (SQL), `semantic_comp_rerank_tool` (Qdrant over transaction descriptions).

```python
def comps_agent_node(state: DealState) -> DealState:
    sql_comps = query_transactions_sql(
        community=state.community, property_type=state.property_type,
        bedrooms=state.bedrooms, budget_range=(state.budget_min, state.budget_max),
        limit=25
    )
    reranked = semantic_rerank(sql_comps, query=state.raw_query, top_k=8)
    state.retrieved_comps = reranked
    state.agent_trace.append({"agent": "comps", "count": len(reranked)})
    return state
```

### 5.4 Agent 3 — Valuation Agent

**Job:** compute a defensible fair-value range from the retrieved comps and *state the method*, not just a number.
**Model:** Claude Sonnet.

**System prompt:**
```
You are the Valuation Agent for Sakan AI. Given the comparable transactions below, compute
a fair-value range for the subject deal. You MUST base your range only on the comps
provided — do not invent market knowledge not present in the data.

COMPS (price, price_per_sqft, date, distance from subject in km):
{retrieved_comps}

SUBJECT: {community}, {property_type}, {bedrooms}BR, budget AED {budget_min}-{budget_max}

Output JSON:
{
  "valuation_low": number,
  "valuation_high": number,
  "valuation_method": string,      // e.g. "median of 6 comps within 1.2km, +/-7% band, adjusted for recency"
  "valuation_rationale": string    // must reference specific comp transaction_ids used
}
```

### 5.5 Agent 4 — Compliance RAG Agent (the core differentiator)

**Job:** retrieve and cite the actual RERA/DLD-style regulatory clauses relevant to this specific deal — never assert a compliance rule that wasn't retrieved.

**Retrieval query composition:** `"{property_type} in {community}, off-plan: {is_off_plan}, RERA Form requirements, escrow, foreign ownership"`, filtered by `doc_category` metadata.

**System prompt:**
```
You are the Compliance RAG Agent for Sakan AI. Ground every statement in the retrieved
regulatory clauses below — never state a compliance requirement that is not present in
the retrieved text. If the retrieved clauses do not clearly cover this deal, say so
explicitly rather than guessing.

DEAL CONTEXT: {deal_summary}
RETRIEVED CLAUSES:
{retrieved_clauses}

Output JSON:
{
  "compliance_flags": [string],       // e.g. ["escrow_verification_required", "form_f_needed"]
  "compliance_summary": string,       // must cite clause_id(s) for every claim made
  "cited_clause_ids": [string]
}
```

**Validation step (implement this, not just the prompt instruction):** after the LLM responds, programmatically check that every `clause_id` in `cited_clause_ids` actually appears in `retrieved_clauses`. If not, reject and retry once, then fall back to `"unable to verify — recommend manual RERA check"` rather than surfacing an unverified claim. This is the same hallucination guardrail pattern as your ClaimGuard project — a strong "I reused this architecture pattern deliberately" interview line.

### 5.6 Agent 5 — Memo Agent

**Job:** synthesize the full state into a clean, cited, investor-ready markdown memo (rendered in the UI and exportable to PDF).

**System prompt:**
```
You are the Memo Agent for Sakan AI. Write a concise, professional deal memo in markdown
using ONLY the data provided below. Structure: Subject Summary, Comparable Transactions
(table), Valuation Range & Method, Compliance Notes (with clause citations), Recommendation.
Keep it under 400 words. Do not add any figures, comps, or regulatory claims not present
in the data below.

DEAL STATE: {full_deal_state_json}
```

### 5.7 LangGraph wiring

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(DealState)
graph.add_node("query", query_agent_node)
graph.add_node("comps", comps_agent_node)
graph.add_node("valuation", valuation_agent_node)
graph.add_node("compliance", compliance_rag_agent_node)
graph.add_node("memo", memo_agent_node)

graph.set_entry_point("query")
graph.add_edge("query", "comps")
graph.add_edge("comps", "valuation")
graph.add_edge("valuation", "compliance")
graph.add_edge("compliance", "memo")
graph.add_edge("memo", END)

deal_pipeline = graph.compile()
```

*(Optional stretch goal, flag it in your build but don't block v1 on it: add a conditional edge after the Query Agent so `query_type == "comps_search"` skips straight to `comps` → `END` without running valuation/compliance/memo — cheaper and faster for simple lookups. This is a good "I thought about cost/latency tradeoffs" talking point.)*

---

## 6. RAG KNOWLEDGE BASE — SYNTHETIC REGULATORY CORPUS

Build a `regulations/` folder of **12 synthetic Markdown documents**, styled after real RERA/DLD structures (write original clause text in that style — do not copy real regulatory text verbatim):

1. `rera_form_a_developer_registration.md`
2. `rera_form_b_unit_reservation.md`
3. `rera_form_f_sale_purchase_agreement.md`
4. `escrow_account_regulations.md`
5. `off_plan_sales_regulation.md`
6. `oqood_pre_registration_process.md`
7. `title_deed_transfer_process.md`
8. `ai_generated_marketing_disclosure_2026.md` — mirrors RERA's real 2026 guideline requiring disclosure of AI-generated property descriptions/images; a nice authentic detail
9. `foreign_ownership_freehold_areas.md`
10. `rental_dispute_center_guidelines.md`
11. `service_charge_regulations.md`
12. `mortgage_registration_requirements.md`

**Chunking:** 300-500 tokens per chunk, metadata = `{doc_id, clause_id, doc_category, applies_to: ["off_plan"|"ready"|"both"]}`.

**Ingestion (`ingest_regulations.py`):** same pattern as your ClaimGuard `ingest_policies.py` — chunk → embed → upsert to a `sakan_regulations` Qdrant collection.

---

## 7. SYNTHETIC DATASET DESIGN

**⚠️ Disclosure to state in your README:** all transaction, building, and developer data is synthetically generated in a realistic DLD-style format. No real DLD data is used or claimed.

> **Update (see README "Data Sources"):** the `transactions` table is now sourced from the real DLD "Transactions" open dataset (via the `alexefimik/dubai-real-estate-transactions-dataset` Kaggle mirror) through `backend/scripts/map_dld_columns.py`, rather than a synthetic generator. `buildings.csv`, `developers.csv`, and `off_plan_projects.csv` remain synthetic as originally specified below, since the real DLD extract does not carry developer track-record or off-plan payment-plan fields at the row level.

### `transactions.csv` (~600 rows)
| Column | Notes |
|---|---|
| transaction_id | `TXN-00001` |
| building_id | FK to buildings.csv |
| community | Business Bay, Dubai Marina, JVC, Downtown, Arabian Ranches, etc. (~15 real community names) |
| property_type | Apartment / Villa / Townhouse |
| bedrooms | 0(studio)-5 |
| size_sqft | realistic per property_type |
| price_aed | realistic distribution per community/type + injected outliers for valuation-edge-case testing |
| price_per_sqft | derived |
| transaction_type | Sale / Off-Plan / Mortgage |
| transaction_date | spread across 18 months |
| registration_type | Oqood / Title Deed |
| buyer_type | Individual / Company |

### `buildings.csv` (~80 rows)
`building_id, name, community, developer_id, completion_status, total_units, avg_price_per_sqft`

### `developers.csv` (~15 rows)
`developer_id, name, track_record_score (0-100), active_projects_count, delivery_delay_rate`

### `off_plan_projects.csv` (~20 rows)
`project_id, name, developer_id, community, launch_date, handover_date, payment_plan_structure, escrow_account_status, rera_registration_number (synthetic), percent_sold`

---

## 8. DATABASE SCHEMA (PostgreSQL DDL)

```sql
CREATE TABLE developers (
    developer_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100),
    track_record_score INT,
    active_projects_count INT,
    delivery_delay_rate NUMERIC(4,2)
);

CREATE TABLE buildings (
    building_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(150),
    community VARCHAR(100),
    developer_id VARCHAR(10) REFERENCES developers(developer_id),
    completion_status VARCHAR(20),
    total_units INT,
    avg_price_per_sqft NUMERIC(10,2)
);

CREATE TABLE transactions (
    transaction_id VARCHAR(15) PRIMARY KEY,
    building_id VARCHAR(10) REFERENCES buildings(building_id),
    community VARCHAR(100),
    property_type VARCHAR(20),
    bedrooms INT,
    size_sqft NUMERIC(8,2),
    price_aed NUMERIC(12,2),
    price_per_sqft NUMERIC(10,2),
    transaction_type VARCHAR(20),
    transaction_date DATE,
    registration_type VARCHAR(20),
    buyer_type VARCHAR(20)
);

CREATE TABLE off_plan_projects (
    project_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(150),
    developer_id VARCHAR(10) REFERENCES developers(developer_id),
    community VARCHAR(100),
    launch_date DATE,
    handover_date DATE,
    payment_plan_structure TEXT,
    escrow_account_status VARCHAR(20),
    rera_registration_number VARCHAR(30),
    percent_sold NUMERIC(5,2)
);

CREATE TABLE deal_queries (
    query_id SERIAL PRIMARY KEY,
    raw_query TEXT,
    query_type VARCHAR(20),
    deal_state JSONB,          -- full DealState snapshot
    agent_trace JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE audit_log (
    log_id SERIAL PRIMARY KEY,
    query_id INT REFERENCES deal_queries(query_id),
    event_type VARCHAR(50),
    event_payload JSONB,
    timestamp TIMESTAMP DEFAULT now()
);
```

---

## 9. API CONTRACTS (FastAPI)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/deals/query` | submit natural-language query, triggers pipeline |
| GET | `/deals/{query_id}` | full result detail |
| GET | `/deals/{query_id}/trace` | agent-by-agent trace |
| GET | `/deals/{query_id}/memo` | download generated memo (markdown → PDF) |
| GET | `/comps` | direct filterable comps search (`?community=&bedrooms=&type=`) |
| GET | `/market/trends` | aggregated analytics for charts |
| GET | `/market/ticker` | recent transactions feed, powers the Transaction Ticker |
| WS | `/ws/deals/{query_id}/stream` | live-stream agent reasoning steps as they run |

---

## 10. FRONTEND BUILD SPEC

**Pages (App Router):**
1. **`/` Command Deck** — header + Transaction Ticker + natural-language query bar + quick market-snapshot cards (avg price/sqft by top 4 communities)
2. **`/deals/[id]` Deal Result** — left: subject + comps table + valuation card + compliance card; right: Agent Trace drawer (collapsible on mobile)
3. **`/comps` Comps Explorer** — Mapbox map with district-level markers + filterable table, syncs selection between map and table
4. **`/deals/[id]/memo` Memo Viewer** — rendered markdown memo, "Export PDF" button
5. **`/market` Analytics** — Recharts: price trend by community, developer track-record leaderboard, off-plan percent-sold funnel

**Non-negotiable UI requirements (from the brief):**
- Full light/dark theme toggle using `next-themes`, implemented exactly per Section 4.4 — test both themes for contrast (WCAG AA minimum) before considering the UI done.
- Every valuation and compliance statement in the UI must show its **citation inline** (comp transaction IDs, RERA clause IDs) — same non-negotiable "explainability visible, not hidden behind a click" rule as ClaimGuard.
- Responsive down to mobile — the Agent Trace drawer becomes a bottom sheet on small screens, not a squeezed sidebar.
- Visible keyboard focus states and `prefers-reduced-motion` respected on the ticker and trace animations.

---

## 11. BUILD PHASES (follow in order; run the smoke test before advancing)

| Phase | Deliverable | Smoke test |
|---|---|---|
| 0 | Repo scaffold, Next.js + Tailwind + shadcn/ui init, Docker Compose (Postgres + Qdrant) | `docker compose up` healthy; `npm run dev` renders a blank themed shell with working toggle |
| 1 | Design tokens + theme toggle (Section 4.4) fully wired | toggling theme changes all colors instantly, no flash, persists on reload |
| 2 | Synthetic dataset generator (`generate_dataset.py`) | all 4 CSVs produced with correct row counts and realistic distributions |
| 3 | DB schema + seed loader | tables populated, row counts match CSVs |
| 4 | Regulatory corpus (12 docs) + ingestion script | Qdrant collection populated; spot-check a similarity query returns sensible clauses |
| 5 | LangGraph pipeline (5 agents wired) | run on 5 sample queries end-to-end, inspect `agent_trace` |
| 6 | FastAPI endpoints (Section 9) | all endpoints respond correctly via `curl`/Postman |
| 7 | Command Deck + Ticker + Query flow | submit a query, watch live trace stream, land on Deal Result page |
| 8 | Comps Explorer map + Analytics page | map/table sync works; charts render from real seeded data |
| 9 | Memo Viewer + PDF export | memo renders with inline citations, PDF export produces a clean document |
| 10 | Polish: README, demo seed data, deploy | live URL works in both themes; README has architecture diagram + ethics note |

---

## 12. BUSINESS DECISIONS (pre-made — do not ask, just build)

- **LLM provider:** Claude API (Sonnet for Valuation/Compliance/Memo, Haiku for Query parsing).
- **Vector DB:** Qdrant, self-hosted via Docker.
- **Maps:** Mapbox GL free tier; if you hit rate limits during demo prep, fall back to `react-leaflet` + OpenStreetMap tiles — either is fine, don't let map cost block the build.
- **Auth:** simple role selector (Agent/Investor/Admin), no real auth system.
- **Dataset scale:** ~600 transactions, ~80 buildings, ~15 developers, ~20 off-plan projects.
- **Default theme:** dark (matches the "terminal" thesis), light fully supported and equally polished — do not treat light mode as an afterthought.
- **Language scope for v1:** English only. Arabic bilingual support is an explicit future improvement (Section 14), not v1 — don't let it expand the build.

---

## 13. EVALUATION METRICS

- **Comps retrieval quality:** manually check 15 queries — are the top comps actually comparable (same community/type/bedroom band, recent date)?
- **Valuation sanity:** compare Valuation Agent output range against the actual `price_aed` of held-out transactions matching the query filters — target the true price falling inside the predicted range >70% of the time.
- **Citation accuracy:** 100% of `cited_clause_ids` must appear in `retrieved_clauses` — enforced programmatically, not just prompted.
- **Pipeline latency:** end-to-end time per full-memo query (target < 20s for demo responsiveness).
- **UI accessibility:** both themes pass WCAG AA contrast on text/background pairs — check with a contrast checker before calling the UI phase done.

---

## 14. LIMITATIONS & ETHICAL CONSIDERATIONS

- All transaction and regulatory data is synthetic, styled after real DLD/RERA structures but not sourced from them — state this explicitly in the README; do not imply this is connected to actual DLD data or systems.
- A production version would need a licensing agreement for real DLD transaction data (which DLD does provide through official channels) and legal review of the regulatory corpus against actual current RERA text.
- Valuation ranges from an 8-comp sample are a demonstration of method, not a certified appraisal — a real deployment would need RICS-qualified valuer sign-off for any client-facing number.
- Off-plan payment-plan and escrow data changes frequently in the real market; a production RAG corpus would need a defined re-ingestion cadence, not a one-time load.
- **Update:** the `transactions` table itself is now populated from the real DLD open dataset (see README "Data Sources"). The buildings/developers/off-plan enrichment tables remain synthetic, so any downstream feature that joins across them (e.g. developer track-record scoring) is still a demonstration of method, not fact, for that portion of the data.

---

## 15. FUTURE IMPROVEMENTS

- Bilingual Arabic query + memo generation (matches the UAE's 60%+ Arabic-speaking market segment)
- Real DLD open-data integration where publicly available, replacing synthetic transactions
- A "portfolio" mode — track multiple deals/queries for a single investor over time, not just one-shot queries
- Developer track-record risk scoring as its own agent (delivery delay prediction from historical handover data)
- WhatsApp integration for query submission, matching how ~70%+ of real Dubai property inquiries actually arrive

---

## 16. VIVA / INTERVIEW Q&A

**Q1: Why does the Compliance RAG Agent matter more than the Valuation Agent?**
Because a wrong valuation is a bad estimate; a wrong compliance claim (telling someone a deal is RERA-clean when it isn't) is a legal and financial liability. That's why it gets the same hallucination guardrail — enforced citation validation, not just a prompt instruction — as the highest-stakes agent in my ClaimGuard project.

**Q2: Why a "terminal" design direction instead of a typical real-estate listings look?**
Because the user isn't browsing listings — they're an analyst who needs to trust dense data fast. I deliberately avoided the warm cream-and-sand palette most Dubai property sites default to, because that's built for browsing, not deciding. A trading-terminal-inspired dark navy and brass system, with monospace numerals, signals "precision instrument" instead of "brochure."

**Q3: How did you decide on the color palette, not just pick colors you liked?**
I ruled out the three most common AI-generated design defaults on purpose — cream+terracotta, near-black+neon, and broadsheet — because none of them fit a data-terminal brief, then built a token system from the actual subject matter: Dubai's own architectural material language (brass, glass, night skyline) reinterpreted as a functional color system, not a decorative one.

**Q4: Why LangGraph over a simpler single LLM call with function-calling?**
Because I need the intermediate state — comps, valuation method, cited clauses — to be inspectable and streamable to the UI as its own trace, not just a final answer. That's the same reasoning as ClaimGuard: the trace *is* the product's trust mechanism, not an implementation detail.

**Q5: What was the hardest part of the RAG design?**
Making the Compliance Agent admit uncertainty. It's tempting to let an LLM always sound confident; the harder, correct design is instructing it to say "insufficient retrieved evidence, recommend manual check" and then actually enforcing that with a programmatic citation check — otherwise you've built a system that lies convincingly instead of one that's honest about its limits.

**Q6: How would this differ from Sakan AI's real-world competitors like PropertyGPT or BayutGPT?**
Those are conversational search — "find me listings." Sakan is agentic deal *intelligence* — it doesn't just retrieve, it computes a valuation, checks compliance, and produces a memo autonomously across multiple reasoning steps. That's the gap the market itself has flagged: everyone's built the marketing layer, almost nobody's built the underwriting layer.

**Q7: What's the biggest limitation as built?**
Synthetic data means the valuation accuracy numbers don't transfer to the real market — the deliverable is the architecture and the explainability pattern, which is exactly what's transferable to a real DLD dataset later.

---

## 17. RESUME / LINKEDIN POSITIONING

**Resume bullet options:**
- *Built Sakan AI, a 5-agent LangGraph deal-intelligence pipeline for Dubai real estate that computes cited valuations and RERA compliance checks via a self-hosted Qdrant RAG pipeline, with a fully custom light/dark UI built in Next.js and Tailwind CSS.*
- *Designed and implemented a hallucination-guardrailed compliance RAG agent enforcing programmatic citation validation on every regulatory claim.*
- *Designed a from-scratch design system (custom color tokens, type system, dark/light theming) rather than a template UI kit, applying a structured design-critique process.*

**30-second elevator pitch:**
*"Dubai's real estate market moved AED 252 billion in Q1 2026 alone, but almost all the AI investment in the sector has gone into marketing — faster listings, faster leads — not the underwriting side: pricing, comps, compliance. I built Sakan AI, a five-agent system that takes a plain-English deal question, pulls real comps, computes a defensible valuation, checks it against RERA compliance rules with cited sources, and generates an investor memo — all with a fully custom terminal-style UI I designed myself, dark and light mode both. It's the same explainability-first agentic pattern that regulated industries here are actively hiring for."*

---

## 18. SUBMISSION CHECKLIST

- [ ] Repo scaffold + Docker Compose running
- [ ] Theme toggle fully functional in both directions, no hydration flash, persists on reload
- [ ] `generate_dataset.py` produces all 4 CSVs with realistic distributions
- [ ] 12 synthetic regulatory documents ingested into Qdrant
- [ ] LangGraph pipeline runs end-to-end, full `agent_trace` visible and streamed live
- [ ] All 8 API endpoints functional
- [ ] Command Deck, Deal Result, Comps Explorer, Memo Viewer, Analytics pages all built
- [ ] Transaction Ticker animates smoothly, respects reduced-motion
- [ ] Every valuation/compliance claim shows inline citation, not hidden behind a click
- [ ] Both themes pass WCAG AA contrast check
- [ ] README with architecture diagram, setup instructions, ethics/limitations section
- [ ] Live deployed URL
- [x] This master prompt doc included in repo as `ARCHITECTURE.md`

---

## 19. DATA SOURCE AMENDMENT — REAL DLD TRANSACTIONS ADAPTER

Section 7 originally specified a fully synthetic `transactions.csv`. That has been superseded for the transactions table specifically: `backend/scripts/map_dld_columns.py` now ingests the real DLD "Transactions" open dataset (mirrored on Kaggle as `alexefimik/dubai-real-estate-transactions-dataset`) directly into Postgres, in place of a generated CSV. See the repo README's "Data Sources" section for the full rationale, the column mapping, and the cleaning rules applied (residential-sale filter, DLD placeholder-row removal, dedup, idempotent upsert). `buildings.csv`, `developers.csv`, and `off_plan_projects.csv` remain synthetic as originally specified, since those enrichment fields (developer track record, payment plans, escrow status) are not present in the public transaction-level extract.
