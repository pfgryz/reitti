from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

import pytest

from experiments import ensure_backend_path
from experiments.astar import interval_stays_with_exact_max, run_astar
from experiments.bruteforce import run_bruteforce
from experiments.cli import Row, _write_outputs, run_ablation, run_boundary
from experiments.matrices import fixture_matrices
from experiments.scenarios import make_scenario

ensure_backend_path()

from core import Point  # noqa: E402
from core.route_optimizer import (  # noqa: E402
    Attraction,
    AttractionType,
    OpeningHours,
    RouteOptimizationInput,
    StayBounds,
    StaySelectionMode,
)


def _objective(
    problem: RouteOptimizationInput, visits: tuple, walk_distance: float
) -> float:
    from core.route_optimizer import ALPHA, BETA

    used = {v.attraction_index: v.departure_time - v.arrival_time for v in visits}
    unused = problem.attractions[0].stay.max
    for i, attr in enumerate(problem.attractions):
        if i == 0:
            continue
        unused += attr.stay.max - used.get(i, 0.0)
    return ALPHA * walk_distance + BETA * unused


async def _walk(visits: tuple, matrices) -> float:
    total = 0.0
    u = 0
    for v in visits:
        total += await matrices.walk_dist.get(u, v.attraction_index)
        u = v.attraction_index
    return total


def test_interval_stays_include_off_grid_max() -> None:
    attraction = Attraction(
        position=Point(lat=60.17, lon=24.94),
        opening_hours=OpeningHours(open=0, close=1440),
        stay=StayBounds(min=30, max=82),
        type=AttractionType.OTHER,
    )
    stays = interval_stays_with_exact_max(
        attraction=attraction,
        arrival=0,
        trip_end=1440,
        mode=StaySelectionMode.INTERVALS_15_MIN,
    )
    assert stays == [30.0, 45.0, 60.0, 75.0, 82.0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "stay_mode",
    [StaySelectionMode.GREEDY, StaySelectionMode.INTERVALS_15_MIN],
)
async def test_astar_and_bruteforce_same_optimum(stay_mode: StaySelectionMode) -> None:
    scenario = make_scenario(
        scenario_id="eq_small",
        seed=777,
        n_attractions=6,
        profile="relaxed",
    )
    problem = RouteOptimizationInput(
        start_time=scenario.problem.start_time,
        attractions=scenario.problem.attractions,
        end_time=scenario.problem.end_time,
        stay_mode=stay_mode,
        heuristic_mode=scenario.problem.heuristic_mode,
    )
    matrices = fixture_matrices(scenario.n_attractions)

    astar_result, _, _ = await run_astar(problem=problem, matrices=matrices)
    brute_result, _, _ = await run_bruteforce(
        problem=problem,
        matrices=matrices,
        timeout_seconds=10.0,
    )

    astar_walk = await _walk(astar_result.visits, matrices)
    brute_walk = await _walk(brute_result.visits, matrices)
    astar_obj = _objective(problem, astar_result.visits, astar_walk)
    brute_obj = _objective(problem, brute_result.visits, brute_walk)
    assert astar_obj == pytest.approx(brute_obj)


@pytest.mark.asyncio
async def test_ablation_contains_no_heuristic_rows() -> None:
    args = argparse.Namespace(
        matrix_mode="fixture",
        database_url=None,
        graphhopper_base_url=None,
        timeout_seconds=2.0,
        seed_count=1,
    )
    rows = await run_ablation(args)
    labels = {r.experiment for r in rows}
    assert "astar_intervals" in labels
    assert "astar_intervals_no_heuristic" in labels


@pytest.mark.asyncio
async def test_boundary_feasibility_flag_computed(tmp_path: Path) -> None:
    args = argparse.Namespace(
        matrix_mode="fixture",
        database_url=None,
        graphhopper_base_url=None,
        timeout_seconds=2.0,
        seed_count=1,
    )
    rows = await run_boundary(args)
    df = _write_outputs(output_dir=tmp_path, rows=rows)
    boundary = df[df["scenario_id"].str.startswith("boundary_")]
    assert not boundary.empty
    assert boundary["feasibility_correctness"].notna().any()


def test_optimality_gap_written(tmp_path: Path) -> None:
    now = datetime.now(UTC).isoformat()
    rows = [
        Row(
            experiment="astar_greedy",
            scenario_id="s1",
            profile="relaxed",
            stay_mode="greedy",
            mode="fixture",
            data_source="fixture_synthetic",
            status="ok",
            n_attractions=5,
            wall_time_ms=10.0,
            peak_memory_mb=1.0,
            expanded_nodes=10,
            generated_nodes=12,
            pruned_by_best_g=1,
            visits_count=4,
            total_stay_minutes=100.0,
            stay_utilization=0.8,
            total_walk_distance_m=1000.0,
            objective_cost=2000.0,
            bf_objective=None,
            optimality_gap=None,
            heuristic_speedup=None,
            feasibility_correctness=None,
            end_time=1000.0,
            seed=1,
            error=None,
            timestamp_utc=now,
        ),
        Row(
            experiment="bruteforce_greedy",
            scenario_id="s1",
            profile="relaxed",
            stay_mode="greedy",
            mode="fixture",
            data_source="fixture_synthetic",
            status="ok",
            n_attractions=5,
            wall_time_ms=12.0,
            peak_memory_mb=1.0,
            expanded_nodes=20,
            generated_nodes=24,
            pruned_by_best_g=2,
            visits_count=4,
            total_stay_minutes=100.0,
            stay_utilization=0.8,
            total_walk_distance_m=1000.0,
            objective_cost=1800.0,
            bf_objective=None,
            optimality_gap=None,
            heuristic_speedup=None,
            feasibility_correctness=None,
            end_time=1000.0,
            seed=1,
            error=None,
            timestamp_utc=now,
        ),
    ]
    df = _write_outputs(output_dir=tmp_path, rows=rows)
    val = float(df[df["experiment"] == "astar_greedy"]["optimality_gap"].iloc[0])
    assert val == pytest.approx((2000.0 - 1800.0) / 1800.0)
