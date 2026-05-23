from __future__ import annotations

import asyncio

from . import ensure_backend_path
from .bruteforce import run_bruteforce
from .scenarios import Scenario
from .types import Variant

ensure_backend_path()

from core.route_optimizer import (  # noqa: E402
    RouteOptimizationInput,
    StaySelectionMode,
    TravelMatrices,
    optimize_route_instrumented,
)


def clone_problem(
    scenario: Scenario, stay_mode: StaySelectionMode
) -> RouteOptimizationInput:
    return RouteOptimizationInput(
        start_time=scenario.problem.start_time,
        attractions=scenario.problem.attractions,
        end_time=scenario.problem.end_time,
        stay_mode=stay_mode,
        heuristic_mode=scenario.problem.heuristic_mode,
    )


async def run_variant(
    *,
    variant: Variant,
    scenario: Scenario,
    matrices: TravelMatrices,
    timeout_seconds: float,
    astar_timeout_seconds: float | None = None,
):
    problem = clone_problem(scenario, variant.stay_mode)
    if variant.algorithm == "astar":
        timeout = (
            timeout_seconds
            if astar_timeout_seconds is None
            else float(astar_timeout_seconds)
        )
        try:
            return await asyncio.wait_for(
                optimize_route_instrumented(
                    problem,
                    matrices,
                    use_heuristic=variant.use_heuristic,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            raise TimeoutError(f"astar timed out after {timeout:.1f}s") from exc
    return await run_bruteforce(
        problem=problem,
        matrices=matrices,
        timeout_seconds=timeout_seconds,
    )
