from app.schemas.trip import TripOptimizeRequest
from core.route_optimizer import AttractionType


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
