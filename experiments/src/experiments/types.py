from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from . import ensure_backend_path

ensure_backend_path()

from core.route_optimizer import StaySelectionMode  # noqa: E402

PipelineProfile = Literal["fast", "full"]
DataMode = Literal["fixture", "real", "both"]


@dataclass(frozen=True, slots=True)
class Variant:
    name: str
    stay_mode: StaySelectionMode
    algorithm: str  # "astar" | "bruteforce"
    use_heuristic: bool = True


VariantsByName = dict[str, Variant]

ASTAR_GREEDY = Variant("astar_greedy", StaySelectionMode.GREEDY, "astar", True)
ASTAR_INTERVALS = Variant(
    "astar_intervals", StaySelectionMode.INTERVALS_15_MIN, "astar", True
)
ASTAR_INTERVALS_NO_H = Variant(
    "astar_intervals_no_heuristic",
    StaySelectionMode.INTERVALS_15_MIN,
    "astar",
    False,
)
BF_GREEDY = Variant("bruteforce_greedy", StaySelectionMode.GREEDY, "bruteforce")
BF_INTERVALS = Variant(
    "bruteforce_intervals",
    StaySelectionMode.INTERVALS_15_MIN,
    "bruteforce",
)
ALL_VARIANTS: VariantsByName = {
    ASTAR_GREEDY.name: ASTAR_GREEDY,
    ASTAR_INTERVALS.name: ASTAR_INTERVALS,
    ASTAR_INTERVALS_NO_H.name: ASTAR_INTERVALS_NO_H,
    BF_GREEDY.name: BF_GREEDY,
    BF_INTERVALS.name: BF_INTERVALS,
}


@dataclass(slots=True)
class Row:
    experiment: str
    scenario_id: str
    profile: str
    suite: str
    setup_name: str
    stay_mode: str
    mode: str
    data_source: str
    status: str
    n_attractions: int
    wall_time_ms: float
    peak_memory_mb: float | None
    expanded_nodes: int | None
    generated_nodes: int | None
    pruned_by_best_g: int | None
    visits_count: int | None
    total_stay_minutes: float | None
    stay_utilization: float | None
    total_walk_distance_m: float | None
    objective_cost: float | None
    bf_objective: float | None
    optimality_gap: float | None
    heuristic_speedup: float | None
    feasibility_correctness: bool | None
    end_time: float | None
    seed: int
    error: str | None
    timestamp_utc: str
