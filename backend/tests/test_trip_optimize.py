from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from core.dependencies import get_client, get_db, get_route_cache
from core.route_optimizer import (
    LegStop,
    PtDetails,
    RouteOptimizationError,
    RouteOptimizationResult,
    TravelLeg,
    TravelMatrices,
    VisitDecision,
)
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


class _FakeLegs:
    def __init__(self, leg: TravelLeg) -> None:
        self._leg = leg

    async def get(self, i: int, j: int) -> TravelLeg:
        return self._leg


def _pt_leg() -> TravelLeg:
    return TravelLeg(
        15.0,
        15000.0,
        250.0,
        "public_transport",
        pt=PtDetails(
            walk_to=((60.17, 24.94), (60.18, 24.95)),
            walk_from=((60.28, 25.03), (60.29, 25.04)),
            from_stop=LegStop("Stop A", 60.18, 24.95),
            to_stop=LegStop("Stop B", 60.28, 25.03),
        ),
    )


def _fake_matrices() -> TravelMatrices:
    return TravelMatrices(_FakeLegs(_pt_leg()))


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
    assert data["distance"] == 15000.0
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

    monkeypatch.setattr(
        "app.routers.trip.optimize_route",
        AsyncMock(return_value=result),
    )
    monkeypatch.setattr(
        "app.routers.trip.create_travel_matrices",
        MagicMock(return_value=_fake_matrices()),
    )

    body = {**VALID_BODY, "include_legs": True}
    response = client.post("/trip/optimize", json=body)

    assert response.status_code == 200
    data = response.json()
    leg = data["legs"][0]
    assert leg["mode"] == "public_transport"
    assert leg["walk_to"] == [[60.17, 24.94], [60.18, 24.95]]
    assert leg["walk_from"] == [[60.28, 25.03], [60.29, 25.04]]
    assert leg["from_stop"]["name"] == "Stop A"
    assert leg["points"] is None


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
