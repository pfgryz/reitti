from __future__ import annotations

import math
import time

from . import ensure_backend_path
from .astar import RunStats, _cost_g, _trip_end, expand_node

ensure_backend_path()

from core.route_optimizer import (  # noqa: E402
    RouteOptimizationError,
    RouteOptimizationInput,
    RouteOptimizationResult,
    SearchNode,
    TravelMatrices,
    validate_preliminary_feasibility,
)


async def run_bruteforce(
    *,
    problem: RouteOptimizationInput,
    matrices: TravelMatrices,
    timeout_seconds: float,
) -> tuple[RouteOptimizationResult, RunStats, float]:
    started = time.perf_counter()
    n = len(problem.attractions)
    if n == 0:
        return RouteOptimizationResult((), problem.start_time), RunStats(), 0.0

    await validate_preliminary_feasibility(problem, matrices)
    goal = (1 << n) - 1
    root = SearchNode(
        u=0,
        visited=1,
        t=problem.start_time,
        d_so_far=0.0,
        unused_so_far=problem.attractions[0].stay.max,
        visits=(),
    )

    stats = RunStats()
    best_goal: SearchNode | None = None
    best_state_cost: dict[tuple[int, int, float], float] = {
        (0, 1, problem.start_time): _cost_g(root)
    }
    stack = [root]

    while stack:
        if (time.perf_counter() - started) > timeout_seconds:
            raise TimeoutError(f"bruteforce timed out after {timeout_seconds:.1f}s")

        node = stack.pop()
        stats.expanded_nodes += 1
        if node.visited == goal:
            if best_goal is None or _cost_g(node) < _cost_g(best_goal):
                best_goal = node
            continue

        successors = await expand_node(node=node, problem=problem, matrices=matrices)
        stats.generated_nodes += len(successors)
        successors.sort(key=_cost_g, reverse=True)
        for nxt in successors:
            key = (nxt.u, nxt.visited, nxt.t)
            cost = _cost_g(nxt)
            if cost >= best_state_cost.get(key, math.inf):
                stats.pruned_by_best_g += 1
                continue
            best_state_cost[key] = cost
            stack.append(nxt)

    if best_goal is None:
        raise RouteOptimizationError("No route found")

    elapsed = (time.perf_counter() - started) * 1000
    return (
        RouteOptimizationResult(best_goal.visits, _trip_end(problem, best_goal)),
        stats,
        elapsed,
    )
