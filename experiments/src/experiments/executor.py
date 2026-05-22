from __future__ import annotations

import tracemalloc
from datetime import UTC, datetime

from tqdm import tqdm

from . import ensure_backend_path
from .astar import run_astar
from .bruteforce import run_bruteforce
from .matrices import load_matrices
from .metrics import _quality, _walk_total
from .scenarios import Scenario
from .types import Row, Variant

ensure_backend_path()

from core.route_optimizer import RouteOptimizationInput, StaySelectionMode  # noqa: E402

BRUTEFORCE_MAX_ATTRACTIONS = 10


def _data_source(mode: str) -> str:
    return "fixture_synthetic" if mode == "fixture" else "graphhopper_gtfs"


def _status_from_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "individually infeasible" in msg or "no route found" in msg:
        return "infeasible"
    if "timed out" in msg:
        return "timeout"
    return "failed"


def _clone_problem(
    scenario: Scenario, stay_mode: StaySelectionMode
) -> RouteOptimizationInput:
    return RouteOptimizationInput(
        start_time=scenario.problem.start_time,
        attractions=scenario.problem.attractions,
        end_time=scenario.problem.end_time,
        stay_mode=stay_mode,
        heuristic_mode=scenario.problem.heuristic_mode,
    )


def _empty_row(
    *,
    variant: Variant,
    scenario: Scenario,
    mode: str,
    status: str,
    error: str | None = None,
) -> Row:
    return Row(
        experiment=variant.name,
        scenario_id=scenario.id,
        profile=scenario.profile,
        stay_mode=variant.stay_mode.value,
        mode=mode,
        data_source=_data_source(mode),
        status=status,
        n_attractions=scenario.n_attractions,
        wall_time_ms=0.0,
        peak_memory_mb=None,
        expanded_nodes=None,
        generated_nodes=None,
        pruned_by_best_g=None,
        visits_count=None,
        total_stay_minutes=None,
        stay_utilization=None,
        total_walk_distance_m=None,
        objective_cost=None,
        bf_objective=None,
        optimality_gap=None,
        heuristic_speedup=None,
        feasibility_correctness=None,
        end_time=None,
        seed=scenario.seed,
        error=error,
        timestamp_utc=datetime.now(UTC).isoformat(),
    )


async def _run_variant(
    *,
    variant: Variant,
    scenario: Scenario,
    mode: str,
    timeout_seconds: float,
    matrices,
) -> Row:
    if (
        variant.algorithm == "bruteforce"
        and scenario.n_attractions > BRUTEFORCE_MAX_ATTRACTIONS
    ):
        return _empty_row(
            variant=variant,
            scenario=scenario,
            mode=mode,
            status="skipped",
            error=f"n_attractions>{BRUTEFORCE_MAX_ATTRACTIONS}",
        )

    problem = _clone_problem(scenario, variant.stay_mode)
    try:
        tracemalloc.start()
        peak_bytes: int | None = None
        try:
            if variant.algorithm == "astar":
                result, stats, wall = await run_astar(
                    problem=problem,
                    matrices=matrices,
                    use_heuristic=variant.use_heuristic,
                )
            else:
                result, stats, wall = await run_bruteforce(
                    problem=problem,
                    matrices=matrices,
                    timeout_seconds=timeout_seconds,
                )
            _, peak_bytes = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        walk = await _walk_total(result.visits, matrices)
        total_stay, utilization, objective = _quality(problem, result.visits, walk)
        return Row(
            experiment=variant.name,
            scenario_id=scenario.id,
            profile=scenario.profile,
            stay_mode=variant.stay_mode.value,
            mode=mode,
            data_source=_data_source(mode),
            status="ok",
            n_attractions=scenario.n_attractions,
            wall_time_ms=wall,
            peak_memory_mb=(peak_bytes / (1024 * 1024))
            if peak_bytes is not None
            else None,
            expanded_nodes=stats.expanded_nodes,
            generated_nodes=stats.generated_nodes,
            pruned_by_best_g=stats.pruned_by_best_g,
            visits_count=len(result.visits),
            total_stay_minutes=total_stay,
            stay_utilization=utilization,
            total_walk_distance_m=walk,
            objective_cost=objective,
            bf_objective=None,
            optimality_gap=None,
            heuristic_speedup=None,
            feasibility_correctness=None,
            end_time=result.end_time,
            seed=scenario.seed,
            error=None,
            timestamp_utc=datetime.now(UTC).isoformat(),
        )
    except Exception as exc:
        return _empty_row(
            variant=variant,
            scenario=scenario,
            mode=mode,
            status=_status_from_error(exc),
            error=str(exc),
        )


async def _run_variants(
    *,
    scenarios: list[Scenario],
    variants: list[Variant],
    mode: str,
    timeout_seconds: float,
    database_url: str | None,
    graphhopper_base_url: str | None,
    desc: str,
) -> list[Row]:
    rows: list[Row] = []
    total = len(scenarios) * len(variants)
    bar = tqdm(total=total, desc=desc, unit="run", leave=False)
    for scenario in scenarios:
        try:
            async with load_matrices(
                scenario=scenario,
                mode=mode,
                database_url=database_url,
                graphhopper_base_url=graphhopper_base_url,
            ) as matrices:
                for variant in variants:
                    rows.append(
                        await _run_variant(
                            variant=variant,
                            scenario=scenario,
                            mode=mode,
                            timeout_seconds=timeout_seconds,
                            matrices=matrices,
                        )
                    )
                    bar.update(1)
        except Exception as exc:
            status = _status_from_error(exc)
            err = str(exc)
            for variant in variants:
                rows.append(
                    _empty_row(
                        variant=variant,
                        scenario=scenario,
                        mode=mode,
                        status=status,
                        error=err,
                    )
                )
                bar.update(1)
    bar.close()
    return rows
