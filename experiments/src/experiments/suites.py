from __future__ import annotations

from typing import Literal

from .scenarios import (
    Scenario,
    make_astar_grid,
    make_bruteforce_grid,
    make_real_slice,
    make_scenario_grid,
)
from .types import PipelineProfile

FAST_GRID_PROFILES = ["relaxed", "tight"]
FAST_ASTAR_GRID_NS = [5, 7, 9, 11]
FAST_BRUTEFORCE_GRID_NS = [5, 6, 7]


def _profile_seed_counts(profile: PipelineProfile) -> tuple[int, int]:
    if profile == "fast":
        return (1, 1)
    return (10, 10)


def _astar_grid_for_profile(
    profile: PipelineProfile, mode: Literal["fixture", "real"]
) -> list[Scenario]:
    if profile == "full":
        return make_astar_grid(seed_count=10)
    if mode == "real":
        return make_real_slice()
    return make_scenario_grid(
        seed_count=1,
        ns=FAST_ASTAR_GRID_NS,
        profiles=FAST_GRID_PROFILES,
        prefix="fast_astar",
        seed_start=12000,
    )


def _bf_grid_for_profile(profile: PipelineProfile, seed_count: int) -> list[Scenario]:
    if profile == "full":
        return make_bruteforce_grid(seed_count=seed_count)
    return make_scenario_grid(
        seed_count=seed_count,
        ns=FAST_BRUTEFORCE_GRID_NS,
        profiles=FAST_GRID_PROFILES,
        prefix="fast_bf",
        seed_start=14000,
    )


def build_mode_suites(
    *,
    profile: PipelineProfile,
    mode: Literal["fixture", "real"],
) -> tuple[list[Scenario], list[Scenario], list[Scenario]]:
    grid_seed_count, ablation_seed_count = _profile_seed_counts(profile)
    astar_grid = _astar_grid_for_profile(profile, mode)
    bf_grid = _bf_grid_for_profile(profile, grid_seed_count)
    ablation_grid = _bf_grid_for_profile(profile, ablation_seed_count)
    return (astar_grid, bf_grid, ablation_grid)
