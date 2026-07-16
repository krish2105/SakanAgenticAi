#!/usr/bin/env python3
"""
One-time (re-run only when the community list changes) helper: resolves
Sakan's canonical Dubai community names to the numeric `location_id`s the
"UAE Real Estate Data API" (RapidAPI, Data API Hub) needs for its
`Transactions` endpoint, and writes them to
scripts/bayut_location_ids.json.

Why a separate, committed mapping file instead of resolving on every
ingestion run: the free RapidAPI plan is capped at a few hundred requests
a month, shared with the actual transaction pulls in
ingest_bayut_transactions.py -- spending 15 of those on autocomplete every
time would be wasteful. Resolve once, commit the result, re-run only if
Sakan starts tracking a new community.

IMPORTANT -- built from the "Location AutoComplete" endpoint's presence in
the API's sidebar, NOT verified against a live call (this sandbox has no
network path to rapidapi.com to test against, same posture as the Dubai
Pulse and licensed-feed integrations elsewhere in this repo). The query
param name below (`query`) is a guess at the common REST convention for
autocomplete endpoints; if the live response is empty or errors, the
printed raw JSON on the first call will show the actual shape needed to
fix `_extract_candidates()` or the param name in one edit.

Usage:
    export RAPIDAPI_KEY=...
    python resolve_bayut_locations.py                  # resolve all, write the file
    python resolve_bayut_locations.py --community "Dubai Marina"  # just one, print only
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from scripts.generate_dataset import COMMUNITIES  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("resolve_bayut_locations")

API_HOST = "uae-real-estate-data-api1.p.rapidapi.com"
AUTOCOMPLETE_URL = f"https://{API_HOST}/location-autocomplete"
OUTPUT_PATH = Path(__file__).resolve().parent / "bayut_location_ids.json"

# Candidate key names to try when parsing an autocomplete result item --
# whichever these have not been confirmed against, so this list widens if
# the real response uses something not yet covered.
ID_KEYS = ("location_id", "id", "locationId")
NAME_KEYS = ("name", "location_name", "title", "label", "text")


def _headers(api_key: str) -> dict:
    return {"x-rapidapi-host": API_HOST, "x-rapidapi-key": api_key}


def _extract_candidates(payload) -> list[dict]:
    """Digs a list of {id, name} candidates out of whatever shape the API
    actually returns -- handles a bare list, or a dict wrapping the list
    under a common key (data/results/locations/suggestions)."""
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = None
        for key in ("data", "results", "locations", "suggestions", "items"):
            val = payload.get(key)
            if isinstance(val, list):
                items = val
                break
            if isinstance(val, dict):
                for inner_key in ("data", "results", "locations", "suggestions", "items"):
                    inner = val.get(inner_key)
                    if isinstance(inner, list):
                        items = inner
                        break
                if items is not None:
                    break
        if items is None:
            return []
    else:
        return []

    candidates = []
    for item in items:
        if not isinstance(item, dict):
            continue
        loc_id = next((item[k] for k in ID_KEYS if k in item), None)
        name = next((item[k] for k in NAME_KEYS if k in item), None)
        if loc_id is not None:
            candidates.append({"id": loc_id, "name": name, "raw": item})
    return candidates


def resolve_one(community: str, api_key: str, verbose: bool) -> dict | None:
    import httpx

    with httpx.Client(timeout=30) as client:
        response = client.get(
            AUTOCOMPLETE_URL, headers=_headers(api_key), params={"query": community}
        )
        response.raise_for_status()
        payload = response.json()

    if verbose:
        log.info("Raw response for %r:\n%s", community, json.dumps(payload, indent=2)[:2000])

    candidates = _extract_candidates(payload)
    if not candidates:
        log.error(
            "Could not find any location candidates for %r in the response. "
            "Check the printed raw JSON above and adjust ID_KEYS/NAME_KEYS or "
            "_extract_candidates() to match its actual shape.",
            community,
        )
        return None

    # Prefer an exact (case-insensitive) name match; fall back to the first result.
    exact = next(
        (c for c in candidates if isinstance(c["name"], str) and c["name"].strip().lower() == community.lower()),
        None,
    )
    chosen = exact or candidates[0]
    if exact is None:
        log.warning(
            "No exact name match for %r; using the top candidate %r (id=%s). Verify this is correct.",
            community,
            chosen["name"],
            chosen["id"],
        )
    return {"location_id": chosen["id"], "matched_name": chosen["name"]}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--community", type=str, default=None, help="Resolve just this one community, print only")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    args = parser.parse_args(argv)

    api_key = config.RAPIDAPI_KEY
    if not api_key:
        raise SystemExit("RAPIDAPI_KEY is not set. See scripts/ingest_bayut_transactions.py's docstring.")

    communities = [args.community] if args.community else COMMUNITIES
    results: dict[str, dict] = {}
    existing = {}
    if OUTPUT_PATH.exists() and not args.community:
        existing = json.loads(OUTPUT_PATH.read_text())

    for i, community in enumerate(communities):
        resolved = resolve_one(community, api_key, verbose=(i == 0))
        if resolved:
            log.info("%-30s -> location_id=%s (matched %r)", community, resolved["location_id"], resolved["matched_name"])
            results[community] = resolved["location_id"]
        if i < len(communities) - 1:
            time.sleep(args.delay)

    if args.community:
        return  # print-only mode, don't touch the committed file

    merged = {**existing, **results}
    OUTPUT_PATH.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n")
    log.info("Wrote %d location IDs to %s", len(merged), OUTPUT_PATH)
    missing = set(COMMUNITIES) - set(merged)
    if missing:
        log.warning("Still unresolved: %s", sorted(missing))


if __name__ == "__main__":
    main()
