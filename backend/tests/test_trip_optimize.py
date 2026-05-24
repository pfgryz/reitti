from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

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


def test_optimize_trip_not_implemented() -> None:
    response = client.post("/trip/optimize", json=VALID_BODY)
    assert response.status_code == 501
    assert response.json()["detail"] == "not implemented"

