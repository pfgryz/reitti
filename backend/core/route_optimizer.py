from dataclasses import dataclass
from enum import Enum

from core import Point

# Cost weights (spec: β ≫ α — stay time dominates, then walking distance)
ALPHA = 1.0  # per meter walked
BETA = 10_000.0  # per minute of unused stay time

STAY_INTERVAL_MINUTES = 15


@dataclass(frozen=True, slots=True)
class OpeningHours:
    open: float
    close: float


class AttractionType(str, Enum):
    MUSEUM = "museum"
    RESTAURANT = "restaurant"
    PARK = "park"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Attraction:
    position: Point
    opening_hours: OpeningHours
    type: AttractionType


@dataclass(frozen=True, slots=True)
class RouteOptimizationInput:
    start_time: float
    attractions: list[Attraction]
    end_time: float | None = None


@dataclass(frozen=True, slots=True)
class SearchState:
    """s = (u, Visited, t) — current attraction, visited bitmask, departure time."""

    u: int
    visited: int
    t: float


def optimize_route() -> None:
    """Find an optimal attraction visit order and stay durations (A*)."""
    raise NotImplementedError
