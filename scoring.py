"""
Normalised Difficulty Scoring Engine
=====================================
Computes a difficulty score (0–100) for a delivery route based on four
workload factors:

  1. Packages     – number of stops / items to deliver
  2. Weight       – total cargo weight in kg
  3. Stairs       – number of stair-climb stops (physical effort)
  4. Distance     – total route distance in km

Each factor is independently normalised using a configurable cap (the
value at which it reaches 100 % contribution).  The factors are then
combined via a weighted average.

Weights (must sum to 1.0):
  packages  : 0.25
  weight    : 0.30
  stairs    : 0.25
  distance  : 0.20

Caps (domain-knowledge estimates for a "hard" delivery day):
  packages  : 60  packages
  weight    : 200 kg
  stairs    : 20  stair-climb stops
  distance  : 100 km
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from models import Route

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FACTOR_WEIGHTS: dict[str, float] = {
    "packages": 0.25,
    "weight":   0.30,
    "stairs":   0.25,
    "distance": 0.20,
}

# "Cap" values — a raw value at or above this cap contributes 100 %
FACTOR_CAPS: dict[str, float] = {
    "packages": 60.0,
    "weight":   200.0,
    "stairs":   20.0,
    "distance": 100.0,
}

assert abs(sum(FACTOR_WEIGHTS.values()) - 1.0) < 1e-9, "Factor weights must sum to 1.0"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_difficulty_score(
    route: "Route",
    *,
    return_breakdown: bool = False,
) -> float | Tuple[float, dict]:
    """
    Returns a normalised difficulty score in [0, 100].

    If *return_breakdown* is True, returns (score, breakdown_dict) where
    breakdown_dict contains raw values, normalised values, and weights for
    each factor.
    """
    raw: dict[str, float] = {
        "packages": float(route.packages),
        "weight":   float(route.total_weight_kg),
        "stairs":   float(route.stairs_count),
        "distance": float(route.distance_km),
    }

    normalised: dict[str, float] = {
        factor: min(value / FACTOR_CAPS[factor], 1.0)
        for factor, value in raw.items()
    }

    score = sum(
        normalised[factor] * FACTOR_WEIGHTS[factor]
        for factor in FACTOR_WEIGHTS
    ) * 100  # scale to 0–100

    if not return_breakdown:
        return round(score, 4)

    breakdown = {
        factor: {
            "raw_value":        raw[factor],
            "cap":              FACTOR_CAPS[factor],
            "normalised":       round(normalised[factor], 4),
            "weight":           FACTOR_WEIGHTS[factor],
            "weighted_contrib": round(normalised[factor] * FACTOR_WEIGHTS[factor] * 100, 4),
        }
        for factor in FACTOR_WEIGHTS
    }

    return round(score, 4), breakdown
