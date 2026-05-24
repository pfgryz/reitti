from __future__ import annotations

from pathlib import Path

import pytest

import random

from experiments.matrices import FixtureMatrixConfig, precompute_fixture_edges
from experiments.scenarios import (
    _sample_walkable_tour,
    build_scenarios,
    setup_from_dict,
    suite_from_dict,
)


def test_build_scenarios_is_deterministic() -> None:
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {
            "variants": ["astar_greedy"],
            "matrix_mode": "fixture",
            "n_attractions": [6, 9],
            "seed_count": 2,
            "profiles": ["relaxed"],
        },
        name="synthetic_main",
    )
    first = build_scenarios(setup=setup, suite=suite)
    second = build_scenarios(setup=setup, suite=suite)
    assert len(first) == 4
    assert [s.id for s in first] == [s.id for s in second]
    assert first[0].suite == "synthetic_main"
    assert first[0].setup_name == "baseline"


@pytest.mark.parametrize("profile", ["relaxed", "tight"])
@pytest.mark.parametrize("n", [6, 9, 12])
def test_generated_scenarios_have_a_feasible_tour_under_runtime_fixture(
    profile: str, n: int
) -> None:
    """Each generated scenario must admit a feasible tour against the same fixture
    seed the executor will use. We reconstruct that tour with the public helper and
    walk it against the produced windows. This is the property the old precheck loop
    failed to guarantee, which produced the runtime CASE-INFEASIBLE warnings."""
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {
            "variants": ["astar_intervals"],
            "matrix_mode": "fixture",
            "n_attractions": [n],
            "seed_count": 6,
            "profiles": [profile],
        },
        name="feasibility_check",
    )
    fixture_cfg = FixtureMatrixConfig()
    for scenario in build_scenarios(setup=setup, suite=suite, fixture_cfg=fixture_cfg):
        times, _ = precompute_fixture_edges(
            scenario.n_attractions, fixture_cfg, seed=scenario.seed
        )
        order, arrivals = _sample_walkable_tour(
            n=scenario.n_attractions,
            times=times,
            setup=setup,
            rng=random.Random(scenario.seed),
        )
        for idx, arrival in zip(order, arrivals, strict=True):
            attr = scenario.problem.attractions[idx]
            assert attr.opening_hours.open <= arrival + 1e-6, scenario.id
            finish = arrival + attr.stay.min
            assert finish <= attr.opening_hours.close + 1e-6, scenario.id
            assert finish <= scenario.problem.end_time + 1e-6, scenario.id


def test_impossible_profile_windows_admit_no_visit() -> None:
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {
            "variants": ["astar_intervals"],
            "matrix_mode": "fixture",
            "n_attractions": [6],
            "seed_count": 2,
            "profiles": ["impossible"],
        },
        name="impossible_check",
    )
    for scenario in build_scenarios(setup=setup, suite=suite):
        for attraction in scenario.problem.attractions[1:]:
            window = attraction.opening_hours.close - attraction.opening_hours.open
            assert attraction.stay.min > window


def test_build_scenarios_includes_handpicked_from_yaml(tmp_path: Path) -> None:
    handpicked = tmp_path / "cases.yaml"
    handpicked.write_text(
        "\n".join(
            [
                "cases:",
                "  - id: custom_boundary",
                "    profile: impossible",
                "    n_attractions: 7",
                "    seed: 9001",
                "",
            ]
        ),
        encoding="utf-8",
    )

    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {
            "variants": ["astar_greedy"],
            "matrix_mode": "fixture",
            "n_attractions": [],
            "seed_count": 0,
            "profiles": [],
            "include_handpicked": True,
            "handpicked_file": str(handpicked),
        },
        name="handpicked_validation",
    )

    scenarios = build_scenarios(setup=setup, suite=suite)
    assert [s.id for s in scenarios] == ["custom_boundary"]
    assert [s.seed for s in scenarios] == [9001]
    assert [s.profile for s in scenarios] == ["impossible"]
    assert [s.n_attractions for s in scenarios] == [7]
    assert all(s.setup_name == "baseline" for s in scenarios)
    assert all(s.suite == "handpicked_validation" for s in scenarios)


def test_build_scenarios_supports_explicit_handpicked_case(tmp_path: Path) -> None:
    handpicked = tmp_path / "explicit_cases.yaml"
    handpicked.write_text(
        "\n".join(
            [
                "cases:",
                "  - id: explicit_case",
                "    case_mode: explicit",
                "    profile: tight",
                "    seed: 123",
                "    start_time: 500",
                "    end_time: 1200",
                "    attractions:",
                "      - open: 540",
                "        close: 660",
                "        min_stay: 20",
                "        max_stay: 40",
                "      - open: 620",
                "        close: 700",
                "        min_stay: 15",
                "        max_stay: 30",
                "",
            ]
        ),
        encoding="utf-8",
    )
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {
            "variants": ["astar_greedy"],
            "matrix_mode": "fixture",
            "n_attractions": [],
            "seed_count": 0,
            "profiles": [],
            "include_handpicked": True,
            "handpicked_file": str(handpicked),
        },
        name="handpicked_explicit",
    )

    scenarios = build_scenarios(setup=setup, suite=suite)
    target = scenarios[0]
    assert target.id == "explicit_case"
    assert target.n_attractions == 3
    assert target.problem.start_time == 500.0
    assert target.problem.end_time == 1200.0
    assert target.problem.attractions[1].opening_hours.open == 540.0
    assert target.problem.attractions[2].stay.max == 30.0


def test_build_scenarios_raises_for_explicit_case_without_attractions(
    tmp_path: Path,
) -> None:
    handpicked = tmp_path / "invalid_explicit.yaml"
    handpicked.write_text(
        "\n".join(
            [
                "cases:",
                "  - id: missing_explicit",
                "    case_mode: explicit",
                "    profile: relaxed",
                "    seed: 7",
                "",
            ]
        ),
        encoding="utf-8",
    )
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {
            "variants": ["astar_greedy"],
            "matrix_mode": "fixture",
            "n_attractions": [],
            "seed_count": 0,
            "profiles": [],
            "include_handpicked": True,
            "handpicked_file": str(handpicked),
        },
        name="handpicked_invalid_explicit",
    )
    with pytest.raises(
        ValueError, match="explicit case attractions must be provided as a list"
    ):
        build_scenarios(setup=setup, suite=suite)


def test_build_scenarios_raises_for_invalid_handpicked_row(tmp_path: Path) -> None:
    handpicked = tmp_path / "invalid_cases.yaml"
    handpicked.write_text(
        "\n".join(
            [
                "cases:",
                "  - id: bad_case",
                "    profile: relaxed",
                "    n_attractions: 0",
                "    seed: 42",
                "",
            ]
        ),
        encoding="utf-8",
    )
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {
            "variants": ["astar_greedy"],
            "matrix_mode": "fixture",
            "n_attractions": [],
            "seed_count": 0,
            "profiles": [],
            "include_handpicked": True,
            "handpicked_file": str(handpicked),
        },
        name="handpicked_invalid",
    )

    with pytest.raises(
        ValueError, match="n_attractions must be an int >= 1"
    ) as exc_info:
        build_scenarios(setup=setup, suite=suite)
    message = str(exc_info.value)
    assert str(handpicked) in message
    assert "bad_case" in message


def test_build_scenarios_raises_for_duplicate_handpicked_ids(tmp_path: Path) -> None:
    handpicked = tmp_path / "duplicate_cases.yaml"
    handpicked.write_text(
        "\n".join(
            [
                "cases:",
                "  - id: duplicate_case",
                "    profile: relaxed",
                "    n_attractions: 6",
                "    seed: 101",
                "  - id: duplicate_case",
                "    profile: tight",
                "    n_attractions: 7",
                "    seed: 202",
                "",
            ]
        ),
        encoding="utf-8",
    )
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {
            "variants": ["astar_greedy"],
            "matrix_mode": "fixture",
            "n_attractions": [],
            "seed_count": 0,
            "profiles": [],
            "include_handpicked": True,
            "handpicked_file": str(handpicked),
        },
        name="handpicked_duplicate",
    )

    with pytest.raises(ValueError, match="duplicate handpicked case id") as exc_info:
        build_scenarios(setup=setup, suite=suite)
    message = str(exc_info.value)
    assert str(handpicked) in message
    assert "duplicate_case" in message
