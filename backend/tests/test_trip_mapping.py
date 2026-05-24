import pytest

from app.schemas.trip import TripOptimizeRequest, from_result
from core.route_optimizer import AttractionType, RouteOptimizationResult, VisitDecision


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


class _FakeMatrixView:
    def __init__(self, values: dict[tuple[int, int], float]) -> None:
        self._values = values

    async def get(self, i: int, j: int) -> float:
        return self._values[(i, j)]


class _FakeMatrices:
    def __init__(self) -> None:
        self.travel_time = _FakeMatrixView({(0, 1): 12.0, (1, 2): 8.0})
        self.walk_dist = _FakeMatrixView({(0, 1): 100.0, (1, 2): 50.0})


@pytest.mark.asyncio
async def test_from_result_maps_visits_and_totals() -> None:
    result = RouteOptimizationResult(
        (
            VisitDecision(1, 610.0, 655.0),
            VisitDecision(2, 670.0, 730.0),
        ),
        end_time=1080.0,
    )
    response = await from_result(result, _FakeMatrices(), [])  # type: ignore[arg-type]

    assert response.end_time == 1080.0
    assert response.travel_time == 20.0
    assert response.walk_distance == 150.0
    assert len(response.visits) == 2
    assert response.visits[0].attraction_index == 1
    assert response.visits[0].arrival_time == 610.0
    assert response.visits[0].departure_time == 655.0
    assert response.visits[0].stay_minutes == 45.0
