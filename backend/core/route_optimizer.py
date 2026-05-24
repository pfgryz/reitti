import heapq
from dataclasses import dataclass
from enum import Enum
from typing import Literal

import httpx
from asyncpg import Pool
from config import (
    MAX_PUBLIC_TRANSPORT_STOPS_TO_CONSIDER,
    MAX_TRAVEL_DISTANCE_TO_PUBLIC_TRANSPORT,
)

from core import Point
from core.exceptions import RouteNotFoundError
from core.lazy_matrix import AsyncLazyMatrix, AsyncMatrixFieldView
from core.route_cache import RouteCache
from core.routing import (
    EProfile,
    RouteSummary,
    calculate_public_transport_route_between,
    calculate_route_between,
)

ALPHA = 1.0
BETA = 10_000.0
STAY_INTERVAL_MINUTES = 15


class RouteOptimizationError(Exception):
    pass


class StaySelectionMode(str, Enum):
    GREEDY = "greedy"
    INTERVALS_15_MIN = "intervals_15_min"


class HeuristicMode(str, Enum):
    BASIC = "basic"
    EXPERIMENTAL_STAY = "experimental_stay"


class AttractionType(str, Enum):
    MUSEUM = "museum"
    RESTAURANT = "restaurant"
    PARK = "park"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class OpeningHours:
    open: float
    close: float


@dataclass(frozen=True, slots=True)
class StayBounds:
    min: float
    max: float


@dataclass(frozen=True, slots=True)
class Attraction:
    position: Point
    opening_hours: OpeningHours
    stay: StayBounds
    type: AttractionType


@dataclass(frozen=True, slots=True)
class RouteOptimizationInput:
    start_time: float
    attractions: list[Attraction]
    end_time: float | None = None
    stay_mode: StaySelectionMode = StaySelectionMode.INTERVALS_15_MIN
    heuristic_mode: HeuristicMode = HeuristicMode.BASIC


@dataclass(frozen=True, slots=True)
class LegStop:
    name: str
    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class PtDetails:
    walk_to: tuple[tuple[float, float], ...]
    walk_from: tuple[tuple[float, float], ...]
    from_stop: LegStop
    to_stop: LegStop


@dataclass(frozen=True, slots=True)
class TravelLeg:
    time: float
    distance: float
    walk_distance: float
    mode: Literal["foot", "public_transport"] = "foot"
    points: tuple[tuple[float, float], ...] | None = None
    pt: PtDetails | None = None


@dataclass(frozen=True, slots=True)
class TravelMatrices:
    legs: AsyncLazyMatrix[TravelLeg]

    @property
    def travel_time(self) -> AsyncMatrixFieldView[TravelLeg, float]:
        return AsyncMatrixFieldView(self.legs, "time")

    @property
    def walk_dist(self) -> AsyncMatrixFieldView[TravelLeg, float]:
        return AsyncMatrixFieldView(self.legs, "walk_distance")


@dataclass(frozen=True, slots=True)
class VisitDecision:
    attraction_index: int
    arrival_time: float
    departure_time: float

    @property
    def stay(self) -> float:
        return self.departure_time - self.arrival_time


@dataclass(frozen=True, slots=True)
class RouteOptimizationResult:
    visits: tuple[VisitDecision, ...]
    end_time: float


@dataclass(frozen=True, slots=True)
class SearchNode:
    u: int
    visited: int
    t: float
    d_so_far: float
    unused_so_far: float
    visits: tuple[VisitDecision, ...]


@dataclass(frozen=True, slots=True)
class RunStats:
    expanded_nodes: int
    generated_nodes: int
    pruned_by_best_g: int


def _nodes_from_mask(mask: int) -> list[int]:
    nodes: list[int] = []
    bit = 0
    while mask:
        if mask & 1:
            nodes.append(bit)
        mask >>= 1
        bit += 1
    return nodes


def _close(attraction: Attraction, trip_end: float | None) -> float:
    close = attraction.opening_hours.close
    return close if trip_end is None else min(close, trip_end)


def trip_end(problem: RouteOptimizationInput, node: SearchNode) -> float:
    if problem.end_time is not None:
        return problem.end_time
    if node.visits:
        i = node.visits[-1].attraction_index
        return problem.attractions[i].opening_hours.close
    return problem.attractions[0].opening_hours.close


def passes_pruning(
    departure: float,
    attraction: Attraction,
    travel_time: float,
    trip_end: float,
) -> bool:
    oh = attraction.opening_hours
    arrival = max(departure + travel_time, oh.open)
    return (
        departure + travel_time <= oh.close
        and arrival + attraction.stay.min <= oh.close
        and arrival + attraction.stay.min <= trip_end
    )


def stay_options(
    attraction: Attraction,
    arrival: float,
    trip_end: float,
    mode: StaySelectionMode,
) -> list[float]:
    max_stay = min(
        attraction.stay.max,
        _close(attraction, trip_end) - arrival,
    )
    if max_stay < attraction.stay.min:
        return []
    if mode == StaySelectionMode.GREEDY:
        return [max_stay]
    out: list[float] = []
    stay = attraction.stay.min
    while stay <= max_stay + 1e-9:
        out.append(stay)
        stay += STAY_INTERVAL_MINUTES
    # Include exact max_stay when it is off the 15-minute grid.
    if out and abs(out[-1] - max_stay) > 1e-9:
        out.append(max_stay)
    return out


async def validate_preliminary_feasibility(
    problem: RouteOptimizationInput,
    matrices: TravelMatrices,
) -> None:
    for index, a in enumerate(problem.attractions):
        close = _close(a, problem.end_time)
        open_t, min_stay = a.opening_hours.open, a.stay.min

        if open_t + min_stay > close:
            raise RouteOptimizationError(
                f"Attraction {index} is individually infeasible."
            )

        if index == 0:
            if max(problem.start_time, open_t) + min_stay > close:
                raise RouteOptimizationError(
                    f"Attraction {index} is individually infeasible."
                )
            continue

        t0 = await matrices.travel_time.get(0, index)
        if max(problem.start_time + t0, open_t) + min_stay <= close:
            continue

        ok = False
        for p, other in enumerate(problem.attractions):
            if p in (0, index):
                continue
            t = await matrices.travel_time.get(p, index)
            arr = max(other.opening_hours.open + other.stay.min + t, open_t)
            if arr + min_stay <= close:
                ok = True
                break
        if not ok:
            raise RouteOptimizationError(
                f"Attraction {index} is individually infeasible."
            )


async def mst_weight(
    nodes: list[int],
    walk_dist: AsyncMatrixFieldView[TravelLeg, float],
) -> float:
    if len(nodes) <= 1:
        return 0.0
    in_tree = {nodes[0]}
    remaining = set(nodes[1:])
    total = 0.0
    while remaining:
        best_d, best_v = float("inf"), None
        for u in in_tree:
            for v in remaining:
                d = await walk_dist.get(u, v)
                if d < best_d:
                    best_d, best_v = d, v
        if best_v is None:
            break
        total += best_d
        in_tree.add(best_v)
        remaining.remove(best_v)
    return total


async def cached_mst_weight(
    u: int,
    n: int,
    visited: int,
    walk_dist: AsyncMatrixFieldView[TravelLeg, float],
    cache: dict[int, float],
) -> float:
    full = (1 << n) - 1
    unvisited = full & ~visited
    mask = unvisited | (1 << u)

    if mask == (1 << u):
        return 0.0
    if mask in cache:
        return cache[mask]

    if unvisited and unvisited in cache:
        min_edge = float("inf")
        for v in _nodes_from_mask(unvisited):
            min_edge = min(min_edge, await walk_dist.get(u, v))
        cache[mask] = cache[unvisited] + min_edge
        return cache[mask]

    nodes = _nodes_from_mask(mask)
    total = await mst_weight(nodes, walk_dist)
    cache[mask] = total
    if unvisited and unvisited not in cache:
        uv = _nodes_from_mask(unvisited)
        if len(uv) > 1:
            cache[unvisited] = await mst_weight(uv, walk_dist)
    return total


async def h_stay(
    node: SearchNode,
    problem: RouteOptimizationInput,
    matrices: TravelMatrices,
) -> float:
    if problem.heuristic_mode == HeuristicMode.BASIC:
        return 0.0
    total = 0.0
    for i, a in enumerate(problem.attractions):
        if node.visited & (1 << i):
            continue
        t = await matrices.travel_time.get(node.u, i)
        arr = max(node.t + t, a.opening_hours.open)
        total += max(0.0, a.stay.max - (a.opening_hours.close - arr))
    return BETA * total


def _leg_from_route(route: RouteSummary, *, pt: bool) -> TravelLeg:
    time_min = route.time / 60
    if not pt:
        return TravelLeg(
            time=time_min,
            distance=route.distance,
            walk_distance=route.distance,
            mode="foot",
            points=tuple(route.points) if route.points else None,
        )
    walk = route.walk_distance if route.walk_distance is not None else route.distance
    pt_details = None
    if route.from_stop and route.to_stop and route.access_points and route.egress_points:
        pt_details = PtDetails(
            walk_to=tuple(route.access_points),
            walk_from=tuple(route.egress_points),
            from_stop=LegStop(
                name=route.from_stop.name,
                lat=route.from_stop.point.lat,
                lon=route.from_stop.point.lon,
            ),
            to_stop=LegStop(
                name=route.to_stop.name,
                lat=route.to_stop.point.lat,
                lon=route.to_stop.point.lon,
            ),
        )
    return TravelLeg(
        time=time_min,
        distance=route.distance,
        walk_distance=walk,
        mode="public_transport",
        pt=pt_details,
    )


def create_travel_matrices(
    attractions: list[Attraction],
    *,
    client: httpx.AsyncClient,
    db: Pool,
    route_cache: RouteCache[RouteSummary],
    include_geometry: bool = False,
) -> TravelMatrices:
    n = len(attractions)
    pts = [a.position for a in attractions]
    zero = TravelLeg(0.0, 0.0, 0.0)

    async def leg(i: int, j: int) -> TravelLeg:
        if i == j:
            return zero

        foot_route = await calculate_route_between(
            client,
            pts[i],
            pts[j],
            EProfile.Foot,
            route_cache,
            include_geometry=False,
        )
        try:
            pt_route = await calculate_public_transport_route_between(
                db,
                client,
                pts[i],
                pts[j],
                MAX_TRAVEL_DISTANCE_TO_PUBLIC_TRANSPORT,
                MAX_PUBLIC_TRANSPORT_STOPS_TO_CONSIDER,
                route_cache,
                include_geometry=False,
                direct_route=foot_route,
            )
        except RouteNotFoundError:
            if include_geometry:
                foot_route = await calculate_route_between(
                    client,
                    pts[i],
                    pts[j],
                    EProfile.Foot,
                    route_cache,
                    include_geometry=True,
                )
            return _leg_from_route(foot_route, pt=False)

        foot_leg = _leg_from_route(foot_route, pt=False)
        pt_leg = _leg_from_route(pt_route, pt=True)
        if pt_leg.time < foot_leg.time:
            if include_geometry:
                pt_route = await calculate_public_transport_route_between(
                    db,
                    client,
                    pts[i],
                    pts[j],
                    MAX_TRAVEL_DISTANCE_TO_PUBLIC_TRANSPORT,
                    MAX_PUBLIC_TRANSPORT_STOPS_TO_CONSIDER,
                    route_cache,
                    include_geometry=True,
                    direct_route=foot_route,
                )
            return _leg_from_route(pt_route, pt=True)

        if include_geometry:
            foot_route = await calculate_route_between(
                client,
                pts[i],
                pts[j],
                EProfile.Foot,
                route_cache,
                include_geometry=True,
            )
        return _leg_from_route(foot_route, pt=False)

    return TravelMatrices(AsyncLazyMatrix(n, leg))


def cost_g(node: SearchNode) -> float:
    return ALPHA * node.d_so_far + BETA * node.unused_so_far


def state_key(node: SearchNode) -> tuple[int, int, float]:
    return (node.u, node.visited, node.t)


async def expand_node(
    node: SearchNode,
    problem: RouteOptimizationInput,
    matrices: TravelMatrices,
) -> list[SearchNode]:
    out: list[SearchNode] = []
    end = trip_end(problem, node)

    for w, a in enumerate(problem.attractions):
        if node.visited & (1 << w):
            continue
        travel = await matrices.travel_time.get(node.u, w)
        if not passes_pruning(node.t, a, travel, end):
            continue

        arrival = max(node.t + travel, a.opening_hours.open)
        walk = await matrices.walk_dist.get(node.u, w)

        for stay in stay_options(a, arrival, end, problem.stay_mode):
            visit = VisitDecision(w, arrival, arrival + stay)
            out.append(
                SearchNode(
                    u=w,
                    visited=node.visited | (1 << w),
                    t=arrival + stay,
                    d_so_far=node.d_so_far + walk,
                    unused_so_far=node.unused_so_far + a.stay.max - stay,
                    visits=node.visits + (visit,),
                )
            )
    return out


async def optimize_route(
    problem: RouteOptimizationInput,
    matrices: TravelMatrices,
    *,
    use_heuristic: bool = True,
) -> RouteOptimizationResult:
    result, _, _ = await optimize_route_instrumented(
        problem,
        matrices,
        use_heuristic=use_heuristic,
    )
    return result


async def optimize_route_instrumented(
    problem: RouteOptimizationInput,
    matrices: TravelMatrices,
    *,
    use_heuristic: bool = True,
) -> tuple[RouteOptimizationResult, RunStats, float]:
    import time

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
    start = SearchNode(
        0, 1, problem.start_time, 0.0, problem.attractions[0].stay.max, ()
    )
    mst_cache: dict[int, float] = {}
    best_g: dict[tuple[int, int, float], float] = {}
    heap: list[tuple[float, float, int, SearchNode]] = []
    seq = 0
    expanded_nodes = 0
    generated_nodes = 0
    pruned_by_best_g = 0

    async def f(node: SearchNode) -> float:
        g = cost_g(node)
        if not use_heuristic:
            return g
        h = ALPHA * await cached_mst_weight(
            node.u, n, node.visited, matrices.walk_dist, mst_cache
        )
        return g + h + await h_stay(node, problem, matrices)

    g0 = cost_g(start)
    best_g[state_key(start)] = g0
    heapq.heappush(heap, (await f(start), g0, seq, start))
    seq += 1

    while heap:
        expanded_nodes += 1
        _, _, _, node = heapq.heappop(heap)
        g = cost_g(node)
        if g > best_g.get(state_key(node), float("inf")):
            continue
        if node.visited == goal:
            elapsed = (time.perf_counter() - started) * 1000.0
            return (
                RouteOptimizationResult(node.visits, node.t),
                RunStats(
                    expanded_nodes=expanded_nodes,
                    generated_nodes=generated_nodes,
                    pruned_by_best_g=pruned_by_best_g,
                ),
                elapsed,
            )

        successors = await expand_node(node, problem, matrices)
        generated_nodes += len(successors)
        for succ in successors:
            gs = cost_g(succ)
            k = state_key(succ)
            if gs >= best_g.get(k, float("inf")):
                pruned_by_best_g += 1
                continue
            best_g[k] = gs
            heapq.heappush(heap, (await f(succ), gs, seq, succ))
            seq += 1

    raise RouteOptimizationError("No route found")
