from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .scenarios import Scenario
from .types import Row, Variant


def data_source(mode: str) -> str:
    if mode == "fixture":
        return "fixture_synthetic"
    if mode == "real":
        return "graphhopper_gtfs"
    raise ValueError(f"Unknown mode for data source: {mode}")


def status_from_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "individually infeasible" in msg or "no route found" in msg:
        return "infeasible"
    if (
        isinstance(exc, (TimeoutError, asyncio.TimeoutError))
        or "timed out" in msg
        or "timeout" in msg
    ):
        return "timeout"
    return "failed"


def row_error(
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
        suite=scenario.suite,
        setup_name=scenario.setup_name,
        stay_mode=variant.stay_mode.value,
        mode=mode,
        data_source=data_source(mode),
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
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )


def row_ok(
    *,
    variant: Variant,
    scenario: Scenario,
    mode: str,
    wall_time_ms: float,
    peak_memory_mb: float | None,
    expanded_nodes: int | None,
    generated_nodes: int | None,
    pruned_by_best_g: int | None,
    visits_count: int,
    total_stay_minutes: float,
    stay_utilization: float,
    total_walk_distance_m: float,
    objective_cost: float,
    end_time: float | None,
) -> Row:
    return Row(
        experiment=variant.name,
        scenario_id=scenario.id,
        profile=scenario.profile,
        suite=scenario.suite,
        setup_name=scenario.setup_name,
        stay_mode=variant.stay_mode.value,
        mode=mode,
        data_source=data_source(mode),
        status="ok",
        n_attractions=scenario.n_attractions,
        wall_time_ms=wall_time_ms,
        peak_memory_mb=peak_memory_mb,
        expanded_nodes=expanded_nodes,
        generated_nodes=generated_nodes,
        pruned_by_best_g=pruned_by_best_g,
        visits_count=visits_count,
        total_stay_minutes=total_stay_minutes,
        stay_utilization=stay_utilization,
        total_walk_distance_m=total_walk_distance_m,
        objective_cost=objective_cost,
        bf_objective=None,
        optimality_gap=None,
        heuristic_speedup=None,
        feasibility_correctness=None,
        end_time=end_time,
        seed=scenario.seed,
        error=None,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )
