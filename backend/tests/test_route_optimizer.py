from unittest.mock import AsyncMock, MagicMock

import pytest

from core import Point
from core.route_cache import RouteCache
from core.route_optimizer import (
    Attraction,
    AttractionType,
    OpeningHours,
    StayBounds,
    TravelLeg,
    create_travel_matrices,
    select_optimal_leg,
)
from core.routing import EProfile, RouteSummary


def test_select_optimal_leg_prefers_faster_foot() -> None:
    foot = TravelLeg(time=20.0, distance=1500.0)
    pt = TravelLeg(time=12.0, distance=400.0)
    chosen = select_optimal_leg(foot, pt)
    assert chosen == pt


def test_select_optimal_leg_prefers_foot_on_tie() -> None:
    foot = TravelLeg(time=10.0, distance=800.0)
    pt = TravelLeg(time=10.0, distance=300.0)
    chosen = select_optimal_leg(foot, pt)
    assert chosen == foot


def test_select_optimal_leg_without_public_transport() -> None:
    foot = TravelLeg(time=15.0, distance=900.0)
    assert select_optimal_leg(foot, None) == foot


@pytest.mark.asyncio
async def test_create_travel_matrices_combines_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    attractions = [
        Attraction(
            position=Point(lat=60.17, lon=24.94),
            opening_hours=OpeningHours(open=540, close=1080),
            stay=StayBounds(min=30, max=90),
            type=AttractionType.MUSEUM,
        ),
        Attraction(
            position=Point(lat=60.18, lon=24.95),
            opening_hours=OpeningHours(open=600, close=1020),
            stay=StayBounds(min=45, max=120),
            type=AttractionType.PARK,
        ),
    ]

    async def mock_foot_route(
        client: object,
        from_point: Point,
        to_point: Point,
        profile: EProfile,
        cache: RouteCache[RouteSummary] | None = None,
        semaphore: object = None,
    ) -> RouteSummary:
        return RouteSummary(distance=1000.0, time=1200.0)

    async def mock_pt_route(
        db: object,
        client: object,
        from_point: Point,
        to_point: Point,
        radius: float,
        max_count: int,
        cache: RouteCache[RouteSummary] | None = None,
    ) -> RouteSummary:
        return RouteSummary(distance=250.0, time=480.0)

    monkeypatch.setattr(
        "core.route_optimizer.calculate_route_between",
        mock_foot_route,
    )
    monkeypatch.setattr(
        "core.route_optimizer.calculate_public_transport_route_between",
        mock_pt_route,
    )

    matrices = create_travel_matrices(
        attractions,
        client=MagicMock(),
        db=MagicMock(),
        route_cache=RouteCache(),
    )

    assert await matrices.foot_time.get(0, 1) == pytest.approx(20.0)
    assert await matrices.foot_distance.get(0, 1) == pytest.approx(1000.0)
    assert await matrices.public_transport_time.get(0, 1) == pytest.approx(8.0)
    assert await matrices.public_transport_distance.get(0, 1) == pytest.approx(250.0)
    assert await matrices.travel_time.get(0, 1) == pytest.approx(8.0)
    assert await matrices.walk_dist.get(0, 1) == pytest.approx(250.0)

    assert matrices.foot_time.is_cached(0, 1)
    assert matrices.travel_time.is_cached(0, 1)
    assert not matrices.foot_time.is_cached(1, 0)
