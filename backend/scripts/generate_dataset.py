#!/usr/bin/env python3
"""
Synthetic dataset generator for Sakan AI (ARCHITECTURE.md Section 7).

Produces four CSVs styled after real DLD/RERA structures, entirely
synthetic — no real DLD data is used or claimed. Output lands in
backend/seed_data/ by default, which IS committed to the repo (small,
demo-scale) so the app is fully demoable without any external
credentials or downloads.

    developers.csv        ~15 rows
    buildings.csv          ~80 rows
    off_plan_projects.csv  ~20 rows
    transactions.csv       ~600 rows (+ a handful of injected outliers)

Note: `backend/scripts/map_dld_columns.py` is the alternative, real-data
path for transactions.csv (see README "Data sources"). This generator's
transactions.csv is the default/demo path.

Usage:
    python generate_dataset.py --out backend/seed_data --seed 42
"""
from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

COMMUNITIES = [
    "Business Bay",
    "Dubai Marina",
    "Jumeirah Village Circle",
    "Downtown Dubai",
    "Arabian Ranches",
    "DAMAC Hills",
    "Dubai South",
    "Mohammed Bin Rashid City",
    "Al Barari",
    "Jumeirah Lake Towers",
    "Palm Jumeirah",
    "Dubai Hills Estate",
    "Al Furjan",
    "Motor City",
    "Dubai Silicon Oasis",
]

# Baseline AED/sqft by community (used to derive realistic prices).
COMMUNITY_BASE_PSF = {
    "Business Bay": 1650,
    "Dubai Marina": 1800,
    "Jumeirah Village Circle": 1100,
    "Downtown Dubai": 2300,
    "Arabian Ranches": 1250,
    "DAMAC Hills": 1150,
    "Dubai South": 950,
    "Mohammed Bin Rashid City": 1900,
    "Al Barari": 1700,
    "Jumeirah Lake Towers": 1450,
    "Palm Jumeirah": 2900,
    "Dubai Hills Estate": 1650,
    "Al Furjan": 1050,
    "Motor City": 1050,
    "Dubai Silicon Oasis": 900,
}

DEVELOPERS = [
    "Emaar Properties",
    "DAMAC Properties",
    "Sobha Realty",
    "Nakheel",
    "Azizi Developments",
    "Danube Properties",
    "Ellington Properties",
    "Meraas",
    "Binghatti Developers",
    "Nshama",
    "Dubai Properties",
    "Deyaar Development",
    "Omniyat",
    "Select Group",
    "Object 1",
]

BUILDING_NAME_TEMPLATES = [
    "{community} Residences",
    "{community} Heights",
    "Marina Gate {n}",
    "Bay Central {n}",
    "Burj Vista {n}",
    "Executive Towers {n}",
    "{community} District {n}",
    "The {community} Views",
    "{community} Gardens",
    "Park {community} {n}",
    "{community} Waterside",
    "Golf {community} {n}",
    "Skyline {community}",
    "{community} Boulevard {n}",
    "Amara {community}",
]

OFF_PLAN_NAME_TEMPLATES = [
    "{developer_short} {community} Waves",
    "Sobha Hartland Waves {n}",
    "Camelia {n}",
    "The Pulse Residence {n}",
    "{community} Crest",
    "Elitz by {developer_short}",
    "{developer_short} Creek Rise {n}",
    "Vela Residences {n}",
]

PAYMENT_PLAN_STRUCTURES = [
    "10/90 — 10% on booking, 90% on handover",
    "20/80 — 20% during construction, 80% post-handover over 3 years",
    "1% monthly during construction, remainder on handover",
    "40/60 — 40% during construction milestones, 60% on handover",
    "30/70 — 30% on booking, 70% split across 4 handover-linked instalments",
]

PROPERTY_TYPE_WEIGHTS = [("Apartment", 0.68), ("Villa", 0.20), ("Townhouse", 0.12)]

BEDROOM_WEIGHTS_BY_TYPE = {
    "Apartment": [(0, 0.12), (1, 0.32), (2, 0.34), (3, 0.18), (4, 0.04)],
    "Villa": [(3, 0.25), (4, 0.40), (5, 0.25), (6, 0.10)],
    "Townhouse": [(2, 0.15), (3, 0.45), (4, 0.35), (5, 0.05)],
}

SIZE_RANGE_BY_TYPE = {
    "Apartment": (420, 2400),
    "Villa": (2800, 7500),
    "Townhouse": (1800, 3600),
}


def weighted_choice(rng: random.Random, weights: list[tuple]):
    items, probs = zip(*weights)
    return rng.choices(items, weights=probs, k=1)[0]


def make_developers(rng: random.Random) -> list[dict]:
    rows = []
    for i, name in enumerate(DEVELOPERS, start=1):
        rows.append(
            {
                "developer_id": f"DEV-{i:02d}",
                "name": name,
                "track_record_score": rng.randint(58, 97),
                "active_projects_count": rng.randint(2, 18),
                "delivery_delay_rate": round(rng.uniform(0.02, 0.28), 2),
            }
        )
    return rows


def make_buildings(rng: random.Random, developers: list[dict], count: int = 80) -> list[dict]:
    rows = []
    used_names: set[str] = set()
    for i in range(1, count + 1):
        community = rng.choice(COMMUNITIES)
        developer = rng.choice(developers)
        template = rng.choice(BUILDING_NAME_TEMPLATES)
        for _ in range(20):
            name = template.format(community=community, n=rng.randint(1, 4))
            if name not in used_names:
                used_names.add(name)
                break
        completion_status = weighted_choice(
            rng, [("Completed", 0.55), ("Under Construction", 0.30), ("Off-Plan", 0.15)]
        )
        base_psf = COMMUNITY_BASE_PSF[community]
        rows.append(
            {
                "building_id": f"BLD-{i:03d}",
                "name": name,
                "community": community,
                "developer_id": developer["developer_id"],
                "completion_status": completion_status,
                "total_units": rng.randint(40, 620),
                "avg_price_per_sqft": round(base_psf * rng.uniform(0.9, 1.15), 2),
            }
        )
    return rows


def make_off_plan_projects(rng: random.Random, developers: list[dict], count: int = 20) -> list[dict]:
    rows = []
    used_names: set[str] = set()
    for i in range(1, count + 1):
        community = rng.choice(COMMUNITIES)
        developer = rng.choice(developers)
        developer_short = developer["name"].split()[0]
        template = rng.choice(OFF_PLAN_NAME_TEMPLATES)
        for _ in range(20):
            name = template.format(developer_short=developer_short, community=community, n=rng.randint(1, 3))
            if name not in used_names:
                used_names.add(name)
                break
        launch = date(2024, 1, 1) + timedelta(days=rng.randint(0, 700))
        handover = launch + timedelta(days=rng.randint(540, 1460))
        rows.append(
            {
                "project_id": f"PRJ-{i:02d}",
                "name": name,
                "developer_id": developer["developer_id"],
                "community": community,
                "launch_date": launch.isoformat(),
                "handover_date": handover.isoformat(),
                "payment_plan_structure": rng.choice(PAYMENT_PLAN_STRUCTURES),
                "escrow_account_status": weighted_choice(
                    rng, [("Active", 0.85), ("Under Review", 0.10), ("Suspended", 0.05)]
                ),
                "rera_registration_number": f"RERA-OP-{launch.year}-{rng.randint(10000, 99999)}",
                "percent_sold": round(rng.uniform(8, 97), 1),
            }
        )
    return rows


@dataclass
class TxnConfig:
    count: int = 600
    outlier_rate: float = 0.02
    days_span: int = 548  # ~18 months


def make_transactions(rng: random.Random, buildings: list[dict], cfg: TxnConfig = TxnConfig()) -> list[dict]:
    rows = []
    start = date.today() - timedelta(days=cfg.days_span)

    for i in range(1, cfg.count + 1):
        building = rng.choice(buildings)
        community = building["community"]
        property_type = weighted_choice(rng, PROPERTY_TYPE_WEIGHTS)
        bedrooms = weighted_choice(rng, BEDROOM_WEIGHTS_BY_TYPE[property_type])

        lo, hi = SIZE_RANGE_BY_TYPE[property_type]
        size_sqft = round(rng.uniform(lo, hi), 0)

        base_psf = float(building["avg_price_per_sqft"])
        is_outlier = rng.random() < cfg.outlier_rate
        noise = rng.uniform(0.4, 2.2) if is_outlier else rng.uniform(0.88, 1.12)
        price_per_sqft = round(base_psf * noise, 2)
        price_aed = round(price_per_sqft * size_sqft, 2)

        transaction_type = weighted_choice(
            rng, [("Sale", 0.62), ("Off-Plan", 0.30), ("Mortgage", 0.08)]
        )
        registration_type = "Oqood" if transaction_type == "Off-Plan" else "Title Deed"
        buyer_type = weighted_choice(rng, [("Individual", 0.78), ("Company", 0.22)])

        txn_date = start + timedelta(days=rng.randint(0, cfg.days_span))

        rows.append(
            {
                "transaction_id": f"TXN-{i:05d}",
                "building_id": building["building_id"],
                "community": community,
                "property_type": property_type,
                "bedrooms": bedrooms,
                "size_sqft": size_sqft,
                "price_aed": price_aed,
                "price_per_sqft": price_per_sqft,
                "transaction_type": transaction_type,
                "transaction_date": txn_date.isoformat(),
                "registration_type": registration_type,
                "buyer_type": buyer_type,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=Path("backend/seed_data"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--transactions", type=int, default=600)
    parser.add_argument("--buildings", type=int, default=80)
    parser.add_argument("--off-plan-projects", type=int, default=20)
    args = parser.parse_args()

    rng = random.Random(args.seed)

    developers = make_developers(rng)
    buildings = make_buildings(rng, developers, count=args.buildings)
    off_plan_projects = make_off_plan_projects(rng, developers, count=args.off_plan_projects)
    transactions = make_transactions(rng, buildings, TxnConfig(count=args.transactions))

    write_csv(args.out / "developers.csv", developers)
    write_csv(args.out / "buildings.csv", buildings)
    write_csv(args.out / "off_plan_projects.csv", off_plan_projects)
    write_csv(args.out / "transactions.csv", transactions)

    print(f"Wrote {len(developers)} developers, {len(buildings)} buildings, "
          f"{len(off_plan_projects)} off-plan projects, {len(transactions)} transactions to {args.out}/")


if __name__ == "__main__":
    main()
