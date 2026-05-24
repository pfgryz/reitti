from core.routing import (
    RouteSummary,
    _path_to_route_summary,
    stitch_point_sequences,
)


def test_path_to_route_summary_without_geometry() -> None:
    summary = _path_to_route_summary({"distance": 100.0, "time": 60_000})
    assert summary == RouteSummary(distance=100.0, time=60.0, points=None)


def test_path_to_route_summary_with_geometry_list() -> None:
    summary = _path_to_route_summary(
        {
            "distance": 100.0,
            "time": 60_000,
            "points_encoded": False,
            "points": [[24.94, 60.17], [24.95, 60.18]],
        },
        include_geometry=True,
    )
    assert summary.points == [(60.17, 24.94), (60.18, 24.95)]


def test_path_to_route_summary_with_geometry_linestring() -> None:
    summary = _path_to_route_summary(
        {
            "distance": 100.0,
            "time": 60_000,
            "points_encoded": False,
            "points": {
                "type": "LineString",
                "coordinates": [[24.956944, 60.17419], [24.931149, 60.174236]],
            },
        },
        include_geometry=True,
    )
    assert summary.points == [(60.17419, 24.956944), (60.174236, 24.931149)]


def test_stitch_point_sequences_deduplicates_junction() -> None:
    seg_a = [(60.0, 24.0), (60.1, 24.1)]
    seg_b = [(60.1, 24.1), (60.2, 24.2)]
    assert stitch_point_sequences([seg_a, seg_b]) == [
        (60.0, 24.0),
        (60.1, 24.1),
        (60.2, 24.2),
    ]


def test_stitch_point_sequences_keeps_distinct_junction() -> None:
    seg_a = [(60.0, 24.0), (60.1, 24.1)]
    seg_b = [(60.11, 24.11), (60.2, 24.2)]
    assert stitch_point_sequences([seg_a, seg_b]) == [
        (60.0, 24.0),
        (60.1, 24.1),
        (60.11, 24.11),
        (60.2, 24.2),
    ]
