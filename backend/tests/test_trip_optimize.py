from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.schemas.trip import FootLegOutput
from core.dependencies import get_client, get_db, get_route_cache
from core.route_optimizer import RouteOptimizationError, RouteOptimizationResult, VisitDecision
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _override_trip_dependencies() -> None:
    app.dependency_overrides[get_client] = lambda: MagicMock()
    app.dependency_overrides[get_db] = lambda: MagicMock()
    app.dependency_overrides[get_route_cache] = lambda: MagicMock()
    yield
    app.dependency_overrides.clear()

VALID_BODY = {
    "start_time": 540,
    "end_time": 1080,
    "attractions": [
        {
            "lat": 60.1718,
            "lon": 24.9414,
            "opening_hours": {"open": 0, "close": 1440},
            "stay": {"min": 0, "max": 30},
            "type": "other",
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


class _FakeMatrixView:
    def __init__(self, values: dict[tuple[int, int], float]) -> None:
        self._values = values

    async def get(self, i: int, j: int) -> float:
        return self._values.get((i, j), 0.0)


def _fake_matrices() -> MagicMock:
    matrices = MagicMock()
    matrices.travel_time = _FakeMatrixView({(0, 1): 15.0})
    matrices.walk_dist = _FakeMatrixView({(0, 1): 250.0})
    return matrices


def test_optimize_trip_success(monkeypatch: pytest.MonkeyPatch) -> None:
    result = RouteOptimizationResult(
        (VisitDecision(1, 600.0, 690.0),),
        end_time=1080.0,
    )

    monkeypatch.setattr(
        "app.routers.trip.optimize_route",
        AsyncMock(return_value=result),
    )
    monkeypatch.setattr(
        "app.routers.trip.create_travel_matrices",
        MagicMock(return_value=_fake_matrices()),
    )

    response = client.post("/trip/optimize", json=VALID_BODY)

    assert response.status_code == 200
    data = response.json()
    assert data["end_time"] == 1080.0
    assert data["travel_time"] == 15.0
    assert data["walk_distance"] == 250.0
    assert len(data["visits"]) == 1
    visit = data["visits"][0]
    assert visit["attraction_index"] == 1
    assert visit["arrival_time"] == 600.0
    assert visit["departure_time"] == 690.0
    assert visit["stay_minutes"] == 90.0


def test_optimize_trip_infeasible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.routers.trip.optimize_route",
        AsyncMock(
            side_effect=RouteOptimizationError(
                "Attraction 1 is individually infeasible."
            )
        ),
    )
    monkeypatch.setattr(
        "app.routers.trip.create_travel_matrices",
        MagicMock(return_value=_fake_matrices()),
    )

    response = client.post("/trip/optimize", json=VALID_BODY)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "ATTRACTION_INFEASIBLE"
    assert "infeasible" in detail["message"]


def test_optimize_trip_include_legs(monkeypatch: pytest.MonkeyPatch) -> None:
    result = RouteOptimizationResult(
        (VisitDecision(1, 600.0, 690.0),),
        end_time=1080.0,
    )
    fake_legs = [
        FootLegOutput(
            from_index=0,
            to_index=1,
            travel_time=15.0,
            walk_distance=250.0,
            points=[(60.17, 24.94), (60.18, 24.93)],
        )
    ]

    monkeypatch.setattr(
        "app.routers.trip.optimize_route",
        AsyncMock(return_value=result),
    )
    monkeypatch.setattr(
        "app.routers.trip.create_travel_matrices",
        MagicMock(return_value=_fake_matrices()),
    )
    monkeypatch.setattr(
        "app.schemas.trip._build_foot_legs",
        AsyncMock(return_value=fake_legs),
    )

    body = {**VALID_BODY, "include_legs": True}
    response = client.post("/trip/optimize", json=body)

    assert response.status_code == 200
    data = response.json()
    assert data["legs"] is not None
    assert len(data["legs"]) == 1
    assert data["legs"][0]["mode"] == "foot"
    assert data["legs"][0]["points"] == [[60.17, 24.94], [60.18, 24.93]]


def test_optimize_trip_no_route(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.routers.trip.optimize_route",
        AsyncMock(side_effect=RouteOptimizationError("No route found")),
    )
    monkeypatch.setattr(
        "app.routers.trip.create_travel_matrices",
        MagicMock(return_value=_fake_matrices()),
    )

    response = client.post("/trip/optimize", json=VALID_BODY)

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "NO_ROUTE_FOUND"
    assert detail["message"] == "No route found"
