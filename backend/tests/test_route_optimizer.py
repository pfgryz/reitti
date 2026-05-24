from unittest.mock import MagicMock

import pytest

from core import Point
from core.exceptions import RouteNotFoundCode, RouteNotFoundError
from core.lazy_matrix import AsyncLazyMatrix, AsyncMatrixFieldView
from core.route_cache import RouteCache
from core.route_optimizer import (
    BETA,
    Attraction,
    AttractionType,
    HeuristicMode,
    OpeningHours,
    RouteOptimizationError,
    RouteOptimizationInput,
    SearchNode,
    StayBounds,
    StaySelectionMode,
    TravelLeg,
    TravelMatrices,
    VisitDecision,
    cached_mst_weight,
    create_travel_matrices,
    h_stay,
    mst_weight,
    optimize_route,
    optimize_route_instrumented,
    passes_pruning,
    stay_options,
    trip_end,
    validate_preliminary_feasibility,
)
from core.routing import RouteSummary

P = Point(lat=60.17, lon=24.94)


def spot(
    open_at: float = 0,
    close: float = 1440,
    min_stay: float = 30,
    max_stay: float = 60,
    kind: AttractionType = AttractionType.MUSEUM,
) -> Attraction:
    return Attraction(
        position=P,
        opening_hours=OpeningHours(open=open_at, close=close),
        stay=StayBounds(min=min_stay, max=max_stay),
        type=kind,
    )


def route_summary(
    distance: float, time: float, *, walk_distance: float | None = None
) -> RouteSummary:
    return RouteSummary(distance=distance, time=time, walk_distance=walk_distance)


def fake_matrices(
    n: int,
    minutes: float = 10.0,
    meters: float = 500.0,
    edges: dict[tuple[int, int], float] | None = None,
) -> TravelMatrices:
    async def fetch(i: int, j: int) -> TravelLeg:
        if i == j:
            return TravelLeg(0.0, 0.0, 0.0)
        d = meters
        if edges:
            d = edges[(i, j)] if (i, j) in edges else edges[(j, i)]
        return TravelLeg(time=minutes, distance=d, walk_distance=d)

    return TravelMatrices(AsyncLazyMatrix(n, fetch))


@pytest.mark.asyncio
async def test_mst_weight() -> None:
    edges = {(0, 1): 10.0, (0, 2): 20.0, (1, 2): 5.0}
    m = fake_matrices(3, edges=edges)
    assert await mst_weight([0, 1, 2], m.walk_dist) == pytest.approx(15.0)


@pytest.mark.asyncio
async def test_cached_mst_cut() -> None:
    m = fake_matrices(3, edges={(0, 1): 10.0, (0, 2): 20.0, (1, 2): 5.0})
    cache: dict[int, float] = {0b110: 5.0}
    w = await cached_mst_weight(0, 3, 0b001, m.walk_dist, cache)
    assert w == pytest.approx(15.0)
    assert cache[0b111] == pytest.approx(15.0)


def test_stay_options() -> None:
    a = spot(max_stay=90)
    assert stay_options(a, 0, 1440, StaySelectionMode.INTERVALS_15_MIN) == [
        30.0,
        45.0,
        60.0,
        75.0,
        90.0,
    ]
    assert stay_options(a, 0, 1440, StaySelectionMode.GREEDY) == [90.0]


def test_stay_options_includes_off_grid_max() -> None:
    a = spot(min_stay=30, max_stay=82)
    assert stay_options(a, 0, 1440, StaySelectionMode.INTERVALS_15_MIN) == [
        30.0,
        45.0,
        60.0,
        75.0,
        82.0,
    ]


def test_trip_end() -> None:
    attrs = [spot(close=1000), spot(close=800, kind=AttractionType.PARK)]
    problem = RouteOptimizationInput(0.0, attrs)
    node = SearchNode(1, 3, 100.0, 0, 0, (VisitDecision(1, 50.0, 100.0),))
    assert trip_end(problem, node) == 800.0

    fixed = RouteOptimizationInput(0.0, [spot()], end_time=500.0)
    assert trip_end(fixed, SearchNode(0, 1, 0.0, 0, 0, ())) == 500.0


@pytest.mark.parametrize(
    "departure,close,trip_end,travel,ok",
    [
        (590, 600, 1440, 15, False),
        (580, 610, 1440, 5, False),
        (100, 1440, 120, 10, False),
        (600, 1080, 1200, 15, True),
    ],
)
def test_passes_pruning(
    departure: float, close: float, trip_end: float, travel: float, ok: bool
) -> None:
    a = spot(close=close)
    assert passes_pruning(departure, a, travel, trip_end) is ok


@pytest.mark.asyncio
async def test_h_stay_experimental() -> None:
    attrs = [spot(close=200, max_stay=100), spot(close=50, max_stay=80, kind=AttractionType.PARK)]
    problem = RouteOptimizationInput(0.0, attrs, heuristic_mode=HeuristicMode.EXPERIMENTAL_STAY)
    node = SearchNode(0, 1, 0.0, 0, 0, ())
    assert await h_stay(node, problem, fake_matrices(2, meters=100)) == pytest.approx(
        BETA * 40.0
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "start,close,msg",
    [(0, 20, "Attraction 1"), (80, 100, "Attraction 1")],
)
async def test_validate_preliminary_rejects(start: float, close: float, msg: str) -> None:
    problem = RouteOptimizationInput(start, [spot(), spot(close=close, kind=AttractionType.PARK)])
    with pytest.raises(RouteOptimizationError, match=msg):
        await validate_preliminary_feasibility(problem, fake_matrices(2))


@pytest.mark.asyncio
async def test_create_travel_matrices(monkeypatch: pytest.MonkeyPatch) -> None:
    attrs = [
        spot(open_at=540, close=1080, max_stay=90),
        spot(open_at=600, close=1020, min_stay=45, max_stay=120, kind=AttractionType.PARK),
    ]

    async def foot(*_a, **_k):
        return route_summary(1000, 1200)

    async def pt(*_a, **_k):
        return route_summary(15000, 480, walk_distance=250)

    monkeypatch.setattr("core.route_optimizer.calculate_route_between", foot)
    monkeypatch.setattr(
        "core.route_optimizer.calculate_public_transport_route_between", pt
    )
    m = create_travel_matrices(attrs, client=MagicMock(), db=MagicMock(), route_cache=RouteCache())

    leg = await m.legs.get(0, 1)
    assert leg.mode == "public_transport"
    assert await m.travel_time.get(0, 1) == pytest.approx(8.0)
    assert await m.walk_dist.get(0, 1) == pytest.approx(250.0)
    assert leg.distance == pytest.approx(15000.0)
    assert m.travel_time.is_cached(0, 1)


@pytest.mark.asyncio
async def test_create_travel_matrices_pt_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    attrs = [spot(), spot(kind=AttractionType.PARK)]

    async def foot(*_a, **_k):
        return route_summary(900, 600)

    async def no_pt(*_a, **_k):
        raise RouteNotFoundError(RouteNotFoundCode.NO_VIABLE_ROUTE, "no pt")

    monkeypatch.setattr("core.route_optimizer.calculate_route_between", foot)
    monkeypatch.setattr(
        "core.route_optimizer.calculate_public_transport_route_between", no_pt
    )
    m = create_travel_matrices(attrs, client=MagicMock(), db=MagicMock(), route_cache=RouteCache())

    assert await m.travel_time.get(0, 1) == pytest.approx(10.0)
    assert await m.walk_dist.get(0, 1) == pytest.approx(900.0)


@pytest.mark.asyncio
async def test_optimize_route() -> None:
    problem = RouteOptimizationInput(0.0, [spot(), spot(kind=AttractionType.PARK)])
    result = await optimize_route(problem, fake_matrices(2))

    assert len(result.visits) == 1
    v = result.visits[0]
    assert v.attraction_index == 1
    assert v.arrival_time == pytest.approx(10.0)
    assert v.stay == pytest.approx(60.0)
    assert result.end_time == pytest.approx(70.0)


@pytest.mark.asyncio
async def test_optimize_route_end_time_is_actual_finish() -> None:
    problem = RouteOptimizationInput(
        540.0,
        [spot(open_at=540, close=1080), spot(open_at=540, close=1080, kind=AttractionType.PARK)],
        end_time=1080.0,
    )
    result = await optimize_route(problem, fake_matrices(2))
    last = result.visits[-1]
    assert result.end_time == pytest.approx(last.departure_time)
    assert result.end_time < 1080.0


@pytest.mark.asyncio
async def test_optimize_route_three_nodes() -> None:
    attrs = [spot(), spot(kind=AttractionType.PARK), spot(kind=AttractionType.OTHER)]
    result = await optimize_route(RouteOptimizationInput(0.0, attrs), fake_matrices(3))
    assert len(result.visits) == 2
    assert {v.attraction_index for v in result.visits} == {1, 2}


@pytest.mark.asyncio
async def test_optimize_route_prefers_short_walk() -> None:
    attrs = [spot(), spot(kind=AttractionType.PARK), spot(kind=AttractionType.OTHER)]
    m = fake_matrices(3, edges={(0, 1): 1000, (0, 2): 100, (1, 2): 100})
    result = await optimize_route(RouteOptimizationInput(0.0, attrs), m)
    assert [v.attraction_index for v in result.visits] == [2, 1]


@pytest.mark.asyncio
async def test_optimize_route_unreachable() -> None:
    problem = RouteOptimizationInput(600.0, [spot(), spot(close=500, kind=AttractionType.PARK)])
    with pytest.raises(RouteOptimizationError):
        await optimize_route(problem, fake_matrices(2))


@pytest.mark.asyncio
async def test_optimize_route_instrumented_returns_stats() -> None:
    problem = RouteOptimizationInput(0.0, [spot(), spot(kind=AttractionType.PARK)])
    result, stats, wall_ms = await optimize_route_instrumented(problem, fake_matrices(2))
    assert len(result.visits) == 1
    assert stats.expanded_nodes > 0
    assert stats.generated_nodes >= 1
    assert stats.pruned_by_best_g >= 0
    assert wall_ms >= 0.0
