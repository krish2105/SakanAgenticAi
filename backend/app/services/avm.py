"""AVM (automated valuation model) -- Phase D of the MVP roadmap: "a
statistical/ML valuation model trained on accumulated proprietary
transaction history, with the LLM reasoning layered on top for
explanation rather than doing the estimation itself."

Predicts price_per_sqft (not absolute price) from community, property_type,
and bedrooms -- DealState never carries the subject unit's size_sqft (a
free-text query like "2BR in Dubai Marina" doesn't specify it), so the
model targets the one price quantity that's comparable across unit sizes.
The Valuation Agent converts this to an absolute price range using the
retrieved comps' own median size_sqft, which it does have.

A Ridge regression on one-hot community/property_type + bedrooms + the
subject building's avg_price_per_sqft, not a deep model -- the seeded
dataset is ~600 rows across ~140 community/type/bedroom combinations
(~4 rows/combo on average), which is not enough data to justify anything
fancier. The point is a real fitted statistical model standing behind the
number instead of a comp-median heuristic, not state-of-the-art accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Building, Transaction

MIN_TRAINING_ROWS = 30


@dataclass
class AVMModel:
    pipeline: object  # sklearn Pipeline
    residual_std: float
    n_training_samples: int
    trained_communities: set[str]
    trained_property_types: set[str]
    # Keyed by community -- used to impute building_avg_price_per_sqft at
    # prediction time, when no specific building is known. Community-level
    # (not global) because communities vary a lot in typical building
    # quality/price -- imputing with a single global median systematically
    # biased predictions toward the mean for every community that isn't
    # near it (caught by comparing predictions against real training rows
    # for Dubai Marina, which came out ~35% low with a global median).
    community_median_building_avg_price_per_sqft: dict[str, float]
    global_median_building_avg_price_per_sqft: float


def _load_training_frame(session: Session, exclude_transaction_ids: set[str] | None = None):
    import pandas as pd

    rows = session.execute(
        select(
            Transaction.transaction_id,
            Transaction.community,
            Transaction.property_type,
            Transaction.bedrooms,
            Transaction.price_per_sqft,
            Building.avg_price_per_sqft,
        ).join(Building, Transaction.building_id == Building.building_id, isouter=True)
    ).all()

    df = pd.DataFrame(
        rows,
        columns=["transaction_id", "community", "property_type", "bedrooms", "price_per_sqft", "building_avg_price_per_sqft"],
    )
    if exclude_transaction_ids:
        df = df[~df["transaction_id"].isin(exclude_transaction_ids)]
    df = df.dropna(subset=["community", "property_type", "bedrooms", "price_per_sqft"])
    df["building_avg_price_per_sqft"] = df["building_avg_price_per_sqft"].fillna(df["price_per_sqft"].median())
    return df


def train_avm(session: Session, exclude_transaction_ids: set[str] | None = None) -> AVMModel | None:
    """Returns None (rather than raising) when there's not enough data to
    train a meaningful model -- callers fall back to the comp-percentile
    heuristic, same graceful-degradation posture as the rest of this app.

    exclude_transaction_ids lets a held-out eval train the model without
    the specific rows it's about to test against -- otherwise the model
    would have literally seen the answer during training, inflating its
    apparent accuracy (see scripts/run_evals.py's AVM check)."""
    df = _load_training_frame(session, exclude_transaction_ids=exclude_transaction_ids)
    if len(df) < MIN_TRAINING_ROWS:
        return None

    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    X = df[["community", "property_type", "bedrooms", "building_avg_price_per_sqft"]]
    y = df["price_per_sqft"].astype(float)

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), ["community", "property_type"]),
        ],
        remainder="passthrough",  # bedrooms, building_avg_price_per_sqft pass through as numeric
    )
    pipeline = Pipeline([("preprocess", preprocessor), ("model", Ridge(alpha=5.0))])
    pipeline.fit(X, y)

    residuals = y.values - pipeline.predict(X)
    residual_std = float(np.std(residuals)) if len(residuals) > 1 else 0.0

    return AVMModel(
        pipeline=pipeline,
        residual_std=residual_std,
        n_training_samples=len(df),
        trained_communities=set(df["community"].unique()),
        trained_property_types=set(df["property_type"].unique()),
        community_median_building_avg_price_per_sqft=df.groupby("community")["building_avg_price_per_sqft"].median().to_dict(),
        global_median_building_avg_price_per_sqft=float(df["building_avg_price_per_sqft"].median()),
    )


def predict_price_per_sqft(
    model: AVMModel, community: str | None, property_type: str | None, bedrooms: int | None
) -> dict | None:
    """Returns {point, low, high, n_training_samples} or None when the
    query is missing fields the model needs, or names a community/type
    never seen in training (OneHotEncoder(handle_unknown="ignore") would
    silently zero those columns instead of erroring, which would quietly
    produce a meaningless prediction -- so this checks explicitly instead)."""
    if not community or not property_type or bedrooms is None:
        return None
    if community not in model.trained_communities or property_type not in model.trained_property_types:
        return None

    import pandas as pd

    # No specific building known at query time (a free-text query doesn't
    # name one) -- impute with this community's own median building price,
    # since Ridge needs a numeric value for every column it was fit on and
    # communities vary too much to use a single global median (see the
    # comment on AVMModel).
    imputed_building_avg = model.community_median_building_avg_price_per_sqft.get(
        community, model.global_median_building_avg_price_per_sqft
    )
    X = pd.DataFrame(
        [
            {
                "community": community,
                "property_type": property_type,
                "bedrooms": bedrooms,
                "building_avg_price_per_sqft": imputed_building_avg,
            }
        ]
    )

    point = float(model.pipeline.predict(X)[0])
    margin = 1.28 * model.residual_std  # ~80% interval under a normal-residual assumption
    return {
        "point": round(point, 2),
        "low": round(max(0.0, point - margin), 2),
        "high": round(point + margin, 2),
        "n_training_samples": model.n_training_samples,
    }
