"""
Fair Load-Balancing Algorithm
==============================
Assigns routes to drivers such that the total cumulative difficulty score
is distributed as evenly as possible across all drivers.

Strategy — Greedy Least-Load Dispatch:
  1. Sort routes in descending order of difficulty (hardest first).
  2. For each route, assign it to the driver with the lowest current
     cumulative score.
  3. Update that driver's cumulative score.
  4. Attach a human-readable explanation to every assignment.

Time complexity: O(R log R + R log D)  (R = routes, D = drivers)
This is optimal for the "makespan minimisation" / list scheduling problem
when using a priority queue — guaranteed ≤ 4/3 OPT.
"""

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING

from models import Assignment

if TYPE_CHECKING:
    from models import Driver, Route


def assign_routes(drivers: list["Driver"], routes: list["Route"]) -> list[Assignment]:
    """
    Fairly assign *routes* to *drivers*.

    Parameters
    ----------
    drivers : list[Driver]
        All available drivers (may already have non-zero cumulative_score
        from prior assignments — these are respected).
    routes : list[Route]
        Unassigned routes to distribute.

    Returns
    -------
    list[Assignment]
        One Assignment record per route, in assignment order.
    """
    if not drivers:
        raise ValueError("At least one driver is required.")
    if not routes:
        return []

    # Min-heap: (cumulative_score, driver_id, driver_name)
    heap: list[tuple[float, str, str]] = [
        (d.cumulative_score, d.id, d.name) for d in drivers
    ]
    heapq.heapify(heap)

    # Sort routes hardest → easiest so large tasks are spread first
    sorted_routes = sorted(routes, key=lambda r: r.difficulty_score, reverse=True)

    assignments: list[Assignment] = []

    for route in sorted_routes:
        # Pop the driver with the lowest load
        current_load, driver_id, driver_name = heapq.heappop(heap)

        explanation = _build_explanation(
            driver_name=driver_name,
            route=route,
            driver_load_before=current_load,
        )

        assignments.append(
            Assignment(
                driver_id=driver_id,
                driver_name=driver_name,
                route_id=route.id,
                route_name=route.name,
                difficulty_score=route.difficulty_score,
                explanation=explanation,
            )
        )

        # Push driver back with updated load
        new_load = current_load + route.difficulty_score
        heapq.heappush(heap, (new_load, driver_id, driver_name))

    return assignments


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_explanation(
    driver_name: str,
    route: "Route",
    driver_load_before: float,
) -> str:
    """
    Returns a transparent, human-readable explanation for why this driver
    was selected for this route — core to AEQUITAS's transparency promise.
    """
    label = _difficulty_label(route.difficulty_score)
    return (
        f"Route '{route.name}' (difficulty {route.difficulty_score:.1f}/100, {label}) "
        f"was assigned to {driver_name} because they had the lowest current "
        f"workload score ({driver_load_before:.1f}) among all available drivers. "
        f"This route involves {route.packages} packages, {route.total_weight_kg} kg, "
        f"{route.stairs_count} stair stop(s), and {route.distance_km} km — "
        f"a balanced assignment that promotes fairness and reduces driver fatigue."
    )


def _difficulty_label(score: float) -> str:
    if score < 30:
        return "Easy"
    if score < 60:
        return "Moderate"
    if score < 80:
        return "Hard"
    return "Extreme"
