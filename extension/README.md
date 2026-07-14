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

- **Re-verified end-to-end** (Phase 13b) as an actual unpacked MV3
  extension in Chromium (`--load-extension`, `headless=new`) against the
  backend as it stands after this session's full Phases 0-12 rewrite (new
  auth/token flow, job durability, billing, everything) -- confirming the
  extension still works against today's API, not just the API that existed
  when it was first built. Options page saves the backend URL; the popup
  renders; a comps search for "Dubai Marina" returns real seeded
  transactions; sign-in gets a real JWT, flips the popup to the signed-in
  view, and the token is confirmed stored in `chrome.storage.local`;
  submitting a full deal check opens a new tab at the correct
  `/deals/{id}` URL (confirmed by polling `context.pages()` for the new
  tab and reading its actual URL/title, not just assuming the API call
  succeeded) and a follow-up `GET /deals` using the extension's own stored
  token confirms the row really was created. Zero console errors
  throughout.
- **New finding from this pass**: the web app doesn't share auth state
  with the extension (different storage: `localStorage` on the app's own
  origin vs. `chrome.storage.local` for the extension) -- a user signed
  into the extension but not into the main site in that browser lands on
  the web app's `/login` page when the handoff tab opens, not directly on
  their deal. Arguably correct behavior (no cross-origin token leakage),
  but worth knowing rather than assuming the handoff always lands signed
  in.
- **Fixed during this pass**: `api.js`'s `login()` previously stored only
  `access_token`, never the `refresh_token` `/auth/login` also returns.
  The extension was never updated when Phase 3 (this session) added
  short-lived (60-minute) access tokens + refresh tokens elsewhere in the
  app, so a signed-in extension session silently started failing after an
  hour with no recovery. Now fixed: `login()` stores both tokens, and a
  new `authedFetch()` helper (used by `me()`/`submitDealQuery()`) retries
  once via `refreshAccessToken()` on a 401 -- the same pattern
  `frontend/lib/api.ts` already uses, scaled down to this extension's two
  authenticated calls. Verified directly: logged in for real, corrupted
  the stored access token to simulate expiry, called `SakanAPI.me()`, and
  confirmed it still returned the right user by silently refreshing first
  (and that the refresh token itself rotated, matching the backend's
  rotate-on-use behavior).
- Still worth doing before shipping this anywhere: a manual pass in an
  actual **windowed** Chrome/Edge -- this sandbox has no GUI, so every
  verification pass here (including this one) is necessarily headless.
  Headless `--load-extension` is a good proxy but isn't the code path most
  real users hit, and a check against the
  [MV3 docs](https://developer.chrome.com/docs/extensions/mv3/intro/) for
  anything headless mode might paper over (permission prompts,
  popup-sizing quirks) is still warranted.
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
