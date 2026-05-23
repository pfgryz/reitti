from __future__ import annotations

import heapq
import time
from dataclasses import dataclass

from . import ensure_backend_path

ensure_backend_path()

from core.route_optimizer import (  # noqa: E402
    ALPHA,
    BETA,
    Attraction,
    RouteOptimizationError,
    RouteOptimizationInput,
    RouteOptimizationResult,
    SearchNode,
    StaySelectionMode,
    TravelMatrices,
    VisitDecision,
    validate_preliminary_feasibility,
)

STAY_INTERVAL_MINUTES = 15.0


@dataclass(slots=True)
class RunStats:
    expanded_nodes: int = 0
    generated_nodes: int = 0
    pruned_by_best_g: int = 0


def _trip_end(problem: RouteOptimizationInput, node: SearchNode) -> float:
    if problem.end_time is not None:
        return problem.end_time
    if node.visits:
        idx = node.visits[-1].attraction_index
        return problem.attractions[idx].opening_hours.close
    return problem.attractions[0].opening_hours.close


def _max_stay(attraction: Attraction, arrival: float, trip_end: float) -> float:
    close = attraction.opening_hours.close
    if trip_end is not None:
        close = min(close, trip_end)
    return min(attraction.stay.max, close - arrival)


def interval_stays_with_exact_max(
    *,
    attraction: Attraction,
    arrival: float,
    trip_end: float,
    mode: StaySelectionMode,
) -> list[float]:
    max_stay = _max_stay(attraction, arrival, trip_end)
    if max_stay < attraction.stay.min:
        return []
    if mode == StaySelectionMode.GREEDY:
        return [max_stay]

    stays: list[float] = []
    current = attraction.stay.min
    while current <= max_stay + 1e-9:
        stays.append(current)
        current += STAY_INTERVAL_MINUTES
    if abs(stays[-1] - max_stay) > 1e-9:
        stays.append(max_stay)
    return stays


def _passes_pruning(
    *,
    departure: float,
    attraction: Attraction,
    travel_time: float,
    trip_end: float,
) -> bool:
    raw_arrival = departure + travel_time
    if raw_arrival > attraction.opening_hours.close:
        return False
    arrival = max(raw_arrival, attraction.opening_hours.open)
    finish_min = arrival + attraction.stay.min
    return finish_min <= attraction.opening_hours.close and finish_min <= trip_end


async def expand_node(
    *,
    node: SearchNode,
    problem: RouteOptimizationInput,
    matrices: TravelMatrices,
) -> list[SearchNode]:
    out: list[SearchNode] = []
    end_time = _trip_end(problem, node)

    for idx, attraction in enumerate(problem.attractions):
        if node.visited & (1 << idx):
            continue

        travel = await matrices.travel_time.get(node.u, idx)
        if not _passes_pruning(
            departure=node.t,
            attraction=attraction,
            travel_time=travel,
            trip_end=end_time,
        ):
            continue

        arrival = max(node.t + travel, attraction.opening_hours.open)
        walk = await matrices.walk_dist.get(node.u, idx)
        stays = interval_stays_with_exact_max(
            attraction=attraction,
            arrival=arrival,
            trip_end=end_time,
            mode=problem.stay_mode,
        )
        for stay in stays:
            visit = VisitDecision(
                attraction_index=idx,
                arrival_time=arrival,
                departure_time=arrival + stay,
            )
            out.append(
                SearchNode(
                    u=idx,
                    visited=node.visited | (1 << idx),
                    t=arrival + stay,
                    d_so_far=node.d_so_far + walk,
                    unused_so_far=node.unused_so_far + attraction.stay.max - stay,
                    visits=node.visits + (visit,),
                )
            )
    return out


def _mask_nodes(mask: int) -> list[int]:
    out: list[int] = []
    bit = 0
    while mask:
        if mask & 1:
            out.append(bit)
        bit += 1
        mask >>= 1
    return out


async def _mst_weight(nodes: list[int], matrices: TravelMatrices) -> float:
    if len(nodes) <= 1:
        return 0.0
    in_tree = {nodes[0]}
    remaining = set(nodes[1:])
    total = 0.0
    while remaining:
        best_d = float("inf")
        best_v: int | None = None
        for u in in_tree:
            for v in remaining:
                dist = await matrices.walk_dist.get(u, v)
                if dist < best_d:
                    best_d = dist
                    best_v = v
        if best_v is None:
            break
        total += best_d
        in_tree.add(best_v)
        remaining.remove(best_v)
    return total


async def _heuristic_mst(
    *,
    current: int,
    n: int,
    visited: int,
    matrices: TravelMatrices,
    mst_cache: dict[int, float],
) -> float:
    full = (1 << n) - 1
    unvisited = full & ~visited
    mask = unvisited | (1 << current)
    if mask in mst_cache:
        return mst_cache[mask]
    weight = await _mst_weight(_mask_nodes(mask), matrices)
    mst_cache[mask] = weight
    return weight


def _state_key(node: SearchNode) -> tuple[int, int, float]:
    return (node.u, node.visited, node.t)


def _cost_g(node: SearchNode) -> float:
    return ALPHA * node.d_so_far + BETA * node.unused_so_far


async def run_astar(
    *,
    problem: RouteOptimizationInput,
    matrices: TravelMatrices,
    use_heuristic: bool = True,
) -> tuple[RouteOptimizationResult, RunStats, float]:
    started = time.perf_counter()
    n = len(problem.attractions)
    if n == 0:
        return RouteOptimizationResult((), problem.start_time), RunStats(), 0.0

    await validate_preliminary_feasibility(problem, matrices)
    goal = (1 << n) - 1
    start = SearchNode(
        u=0,
        visited=1,
        t=problem.start_time,
        d_so_far=0.0,
        unused_so_far=problem.attractions[0].stay.max,
        visits=(),
    )

    best_g: dict[tuple[int, int, float], float] = {_state_key(start): _cost_g(start)}
    mst_cache: dict[int, float] = {}
    stats = RunStats()
    heap: list[tuple[float, float, int, SearchNode]] = []
    seq = 0

    h0 = 0.0
    if use_heuristic:
        h0 = ALPHA * await _heuristic_mst(
            current=start.u,
            n=n,
            visited=start.visited,
            matrices=matrices,
            mst_cache=mst_cache,
        )
    heapq.heappush(heap, (_cost_g(start) + h0, _cost_g(start), seq, start))
    seq += 1

    while heap:
        stats.expanded_nodes += 1
        _, _, _, node = heapq.heappop(heap)
        g = _cost_g(node)
        if g > best_g.get(_state_key(node), float("inf")):
            continue
        if node.visited == goal:
            elapsed = (time.perf_counter() - started) * 1000
            return (
                RouteOptimizationResult(node.visits, _trip_end(problem, node)),
                stats,
                elapsed,
            )

        successors = await expand_node(node=node, problem=problem, matrices=matrices)
        stats.generated_nodes += len(successors)
        for nxt in successors:
            g_next = _cost_g(nxt)
            key = _state_key(nxt)
            if g_next >= best_g.get(key, float("inf")):
                stats.pruned_by_best_g += 1
                continue
            best_g[key] = g_next
            h_next = 0.0
            if use_heuristic:
                h_next = ALPHA * await _heuristic_mst(
                    current=nxt.u,
                    n=n,
                    visited=nxt.visited,
                    matrices=matrices,
                    mst_cache=mst_cache,
                )
            heapq.heappush(heap, (g_next + h_next, g_next, seq, nxt))
            seq += 1

    raise RouteOptimizationError("No route found")
