from __future__ import annotations

import math
import time

from . import ensure_backend_path

ensure_backend_path()

from core.route_optimizer import (  # noqa: E402
    RouteOptimizationError,
    RouteOptimizationInput,
    RouteOptimizationResult,
    RunStats,
    SearchNode,
    TravelMatrices,
    cost_g,
    expand_node,
    state_key,
    trip_end,
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
        return (
            RouteOptimizationResult((), problem.start_time),
            RunStats(expanded_nodes=0, generated_nodes=0, pruned_by_best_g=0),
            0.0,
        )

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

    expanded_nodes = 0
    generated_nodes = 0
    pruned_by_best_g = 0
    best_goal: SearchNode | None = None
    best_state_cost: dict[tuple[int, int, float], float] = {
        state_key(root): cost_g(root)
    }
    stack = [root]

    while stack:
        if (time.perf_counter() - started) > timeout_seconds:
            raise TimeoutError(f"bruteforce timed out after {timeout_seconds:.1f}s")

        node = stack.pop()
        expanded_nodes += 1
        if node.visited == goal:
            if best_goal is None or cost_g(node) < cost_g(best_goal):
                best_goal = node
            continue

        successors = await expand_node(node, problem, matrices)
        generated_nodes += len(successors)
        successors.sort(key=cost_g, reverse=True)
        for nxt in successors:
            key = state_key(nxt)
            node_cost = cost_g(nxt)
            if node_cost >= best_state_cost.get(key, math.inf):
                pruned_by_best_g += 1
                continue
            best_state_cost[key] = node_cost
            stack.append(nxt)

    if best_goal is None:
        raise RouteOptimizationError("No route found")

    elapsed = (time.perf_counter() - started) * 1000.0
    return (
        RouteOptimizationResult(best_goal.visits, trip_end(problem, best_goal)),
        RunStats(
            expanded_nodes=expanded_nodes,
            generated_nodes=generated_nodes,
            pruned_by_best_g=pruned_by_best_g,
        ),
        elapsed,
    )
