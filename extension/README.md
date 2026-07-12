# Sakan AI browser extension (skeleton)

Phase C of the MVP roadmap: "A Chrome extension or CRM plugin — surfacing a
valuation/compliance check inline on a listing page... beats a standalone
app for adoption." This is a working skeleton of that, not a finished
product — see "What's real vs. not" below before treating it as launch-ready.

## What it does

- **Popup** (click the toolbar icon): sign in against the real backend
  (`/auth/login`), search comps (`/comps`, no login needed), or submit a
  full deal query (`/deals/query`, requires sign-in) which opens the real
  web app's Deal Result page in a new tab — the popup doesn't reimplement
  the streaming trace UI in 320px, it hands off to the app that already has it.
- **Right-click → "Check with Sakan AI"** on selected text anywhere:
  stashes the selection and pre-fills the popup's deal-query box next time
  you open it (MV3 service workers can't open the toolbar popup
  programmatically, so this is the closest equivalent).
- **Floating button** on bayut.com / propertyfinder.ae listing pages:
  opens the popup as a full tab. Does **not** scrape the listing's price
  or details off the page — see below.

## Load it locally

1. `chrome://extensions` → enable **Developer mode** → **Load unpacked** →
   select this `extension/` directory.
2. Click the toolbar icon's gear (⚙) to set the backend URL (defaults to
   `http://localhost:8000`).
3. Start the backend (`cd backend && uvicorn app.main:app --reload`) and
   try a comps search — works without signing in.

## What's real vs. not

- **Verified for real, loaded as an actual unpacked MV3 extension** in
  Chromium (`--load-extension`, headless=new) against the real running
  FastAPI backend: the background service worker registers, the popup
  renders, a comps search for "Dubai Marina" returns real seeded
  transactions, sign-in gets a real JWT and flips the popup to the
  signed-in view, and submitting a full deal query creates a real
  `deal_queries` row and opens a new tab at `/deals/{id}` (confirmed the
  tab-open mechanism works; the tab itself 404's in this sandbox's test
  session only because that session's frontend happened to be running on
  a non-default port, not because of an extension bug). Zero console
  errors across all of that.
- Still worth doing before shipping this anywhere: a manual pass in an
  actual windowed Chrome/Edge (not just headless), since headless
  extension loading is not the code path most users hit, and a check
  against the [MV3 docs](https://developer.chrome.com/docs/extensions/mv3/intro/)
  for anything headless mode might paper over (permission prompts,
  popup-sizing quirks).
- **Does not scrape listing pages.** bayut.com's and propertyfinder.ae's
  real DOM structure isn't accessible from this sandbox to build and
  verify a scraper against, and a guessed CSS selector breaks silently the
  moment either site's markup changes — worse than not extracting
  anything. The floating button is a visible entry point, not an
  auto-fill. Real field extraction (price, community, bedrooms straight
  off the listing) is a follow-up, not faked here.
- `host_permissions` in `manifest.json` only covers `localhost:8000` and
  `*.onrender.com` — point it at your actual backend domain before using
  this against a real deployment.
- No packaging/publishing to the Chrome Web Store is set up; this is a
  local-unpacked skeleton.
