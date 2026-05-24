import pytest

from app.schemas.trip import TripOptimizeRequest, from_result
from core.route_optimizer import (
    AttractionType,
    LegStop,
    PtDetails,
    RouteOptimizationResult,
    TravelLeg,
    TravelMatrices,
    VisitDecision,
)


def test_to_problem():
    req = TripOptimizeRequest.model_validate(
        {
            "start_time": 540,
            "end_time": 1080,
            "attractions": [
                {
                    "lat": 60.1718,
                    "lon": 24.9414,
                    "opening_hours": {"open": 0, "close": 1440},
                    "stay": {"min": 0, "max": 0},
                },
                {
                    "lat": 60.1749,
                    "lon": 24.9314,
                    "opening_hours": {"open": 600, "close": 1200},
                    "stay": {"min": 45, "max": 90},
                    "type": "museum",
                },
            ],
        }
    )
    p = req.to_problem()
    assert p.start_time == 540
    assert p.end_time == 1080
    assert len(p.attractions) == 2
    assert p.attractions[1].type == AttractionType.MUSEUM


class _FakeLegs:
    def __init__(self, legs: dict[tuple[int, int], TravelLeg]) -> None:
        self._legs = legs

    async def get(self, i: int, j: int) -> TravelLeg:
        return self._legs[(i, j)]


@pytest.mark.asyncio
async def test_from_result_maps_visits_and_totals() -> None:
    result = RouteOptimizationResult(
        (
            VisitDecision(1, 610.0, 655.0),
            VisitDecision(2, 670.0, 730.0),
        ),
        end_time=1080.0,
    )
    matrices = TravelMatrices(
        _FakeLegs(
            {
                (0, 1): TravelLeg(12, 100, 100, "foot"),
                (1, 2): TravelLeg(8, 50, 50, "foot"),
            }
        )
    )
    response = await from_result(result, matrices, include_legs=False)

    assert response.end_time == 1080.0
    assert response.travel_time == 20.0
    assert response.walk_distance == 150.0
    assert response.distance == 150.0
    assert len(response.visits) == 2
    assert response.visits[0].attraction_index == 1
    assert response.visits[0].arrival_time == 610.0
    assert response.visits[0].departure_time == 655.0
    assert response.visits[0].stay_minutes == 45.0


@pytest.mark.asyncio
async def test_from_result_builds_legs() -> None:
    result = RouteOptimizationResult(
        (VisitDecision(1, 600.0, 690.0),),
        end_time=1080.0,
    )
    matrices = TravelMatrices(
        _FakeLegs(
            {
                (0, 1): TravelLeg(
                    15,
                    15000,
                    400,
                    "public_transport",
                    pt=PtDetails(
                        walk_to=((60.17, 24.94), (60.18, 24.95)),
                        walk_from=((60.28, 25.03), (60.29, 25.04)),
                        from_stop=LegStop("A", 60.18, 24.95),
                        to_stop=LegStop("B", 60.28, 25.03),
                    ),
                ),
            }
        )
    )
    response = await from_result(result, matrices, include_legs=True)

    assert response.legs is not None
    leg = response.legs[0]
    assert leg.mode == "public_transport"
    assert leg.walk_distance == 400.0
    assert leg.walk_to is not None
    assert leg.from_stop is not None
    assert leg.points is None
