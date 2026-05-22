from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

from . import ensure_backend_path

ensure_backend_path()

from core import Point  # noqa: E402
from core.route_optimizer import (  # noqa: E402
    Attraction,
    AttractionType,
    OpeningHours,
    RouteOptimizationInput,
    StayBounds,
)

WindowProfile = Literal["relaxed", "tight", "impossible"]
A_STAR_GRID_NS = [5, 7, 9, 11, 13, 15, 18, 22]
BRUTEFORCE_GRID_NS = [5, 6, 7, 8, 9, 10]
GRID_PROFILES: list[WindowProfile] = ["relaxed", "tight", "impossible"]


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    seed: int
    n_attractions: int
    profile: WindowProfile
    problem: RouteOptimizationInput


def _attraction(
    *,
    lat: float,
    lon: float,
    open_at: float,
    close_at: float,
    min_stay: float,
    max_stay: float,
) -> Attraction:
    return Attraction(
        position=Point(lat=lat, lon=lon),
        opening_hours=OpeningHours(open=open_at, close=close_at),
        stay=StayBounds(min=min_stay, max=max_stay),
        type=AttractionType.OTHER,
    )


def make_scenario(
    *,
    scenario_id: str,
    seed: int,
    n_attractions: int,
    profile: WindowProfile = "relaxed",
) -> Scenario:
    rng = random.Random(seed)
    start_time = 8 * 60
    trip_end = 22 * 60
    base_lat = 60.1700
    base_lon = 24.9410

    attractions = [
        _attraction(
            lat=base_lat,
            lon=base_lon,
            open_at=0,
            close_at=24 * 60,
            min_stay=0,
            max_stay=0,
        )
    ]

    for _ in range(1, n_attractions):
        lat = base_lat + rng.uniform(-0.01, 0.01)
        lon = base_lon + rng.uniform(-0.01, 0.01)

        min_stay = rng.choice([10, 15, 20, 25])
        max_stay = min_stay + rng.choice([10, 15, 20, 30, 45])

        if profile == "tight":
            open_at = rng.randint(9 * 60, 11 * 60)
            close_at = open_at + rng.choice([60, 75, 90, 120])
        elif profile == "impossible":
            open_at = rng.randint(13 * 60, 15 * 60)
            close_at = open_at + rng.choice([15, 20, 25])
            min_stay = max(min_stay, 30)
            max_stay = max(max_stay, min_stay)
        else:
            open_at = start_time
            close_at = trip_end

        attractions.append(
            _attraction(
                lat=lat,
                lon=lon,
                open_at=open_at,
                close_at=close_at,
                min_stay=min_stay,
                max_stay=max_stay,
            )
        )

    return Scenario(
        id=scenario_id,
        seed=seed,
        n_attractions=n_attractions,
        profile=profile,
        problem=RouteOptimizationInput(
            start_time=start_time,
            attractions=attractions,
            end_time=trip_end,
        ),
    )


def make_scenario_grid(
    *,
    seed_count: int,
    ns: list[int],
    profiles: list[WindowProfile],
    prefix: str,
    seed_start: int = 1000,
) -> list[Scenario]:
    out: list[Scenario] = []
    for n in ns:
        for profile in profiles:
            for sidx in range(seed_count):
                seed = seed_start + n * 100 + sidx
                out.append(
                    make_scenario(
                        scenario_id=f"{prefix}_{profile}_n{n}_s{sidx}",
                        seed=seed,
                        n_attractions=n,
                        profile=profile,
                    )
                )
    return out


def make_astar_grid(*, seed_count: int = 10) -> list[Scenario]:
    return make_scenario_grid(
        seed_count=seed_count,
        ns=A_STAR_GRID_NS,
        profiles=GRID_PROFILES,
        prefix="grid_astar",
        seed_start=2000,
    )


def make_bruteforce_grid(*, seed_count: int = 10) -> list[Scenario]:
    return make_scenario_grid(
        seed_count=seed_count,
        ns=BRUTEFORCE_GRID_NS,
        profiles=GRID_PROFILES,
        prefix="grid_bf",
        seed_start=6000,
    )


def make_real_slice() -> list[Scenario]:
    return [
        make_scenario(
            scenario_id=f"real_relaxed_n{n}_s0",
            seed=9000 + n,
            n_attractions=n,
            profile="relaxed",
        )
        for n in [6, 9, 12]
    ]


def make_boundary_scenarios() -> list[Scenario]:
    impossible_all = make_scenario(
        scenario_id="boundary_all_impossible",
        seed=7771,
        n_attractions=8,
        profile="impossible",
    )

    unreachable_one = make_scenario(
        scenario_id="boundary_single_unreachable",
        seed=7772,
        n_attractions=6,
        profile="relaxed",
    )
    attrs = list(unreachable_one.problem.attractions)
    target = attrs[1]
    attrs[1] = Attraction(
        position=target.position,
        opening_hours=OpeningHours(open=300.0, close=320.0),
        stay=StayBounds(min=45.0, max=60.0),
        type=target.type,
    )
    unreachable_one = Scenario(
        id=unreachable_one.id,
        seed=unreachable_one.seed,
        n_attractions=unreachable_one.n_attractions,
        profile=unreachable_one.profile,
        problem=RouteOptimizationInput(
            start_time=unreachable_one.problem.start_time,
            attractions=attrs,
            end_time=unreachable_one.problem.end_time,
        ),
    )

    empty_only_start = Scenario(
        id="boundary_empty_only_start",
        seed=7773,
        n_attractions=1,
        profile="relaxed",
        problem=RouteOptimizationInput(
            start_time=8 * 60,
            attractions=[
                _attraction(
                    lat=60.1700,
                    lon=24.9410,
                    open_at=0.0,
                    close_at=24 * 60,
                    min_stay=0.0,
                    max_stay=0.0,
                )
            ],
            end_time=22 * 60,
        ),
    )

    timeout_case = make_scenario(
        scenario_id="boundary_timeout_bf",
        seed=7774,
        n_attractions=10,
        profile="relaxed",
    )

    return [impossible_all, unreachable_one, empty_only_start, timeout_case]
