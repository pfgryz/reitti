from __future__ import annotations

from pathlib import Path

import pytest

import experiments.scenarios as scenarios_mod
from experiments.scenarios import build_scenarios, setup_from_dict, suite_from_dict


def test_build_scenarios_is_deterministic() -> None:
    setup = setup_from_dict(
        {
            "profiles": ["relaxed"],
            "n_attractions": [6, 9],
            "seed_count": 2,
        },
        name="baseline",
    )
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


def test_relaxed_uses_fallback_when_precheck_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scenarios_mod, "_is_problem_precheck_feasible", lambda _: False
    )
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {
            "variants": ["astar_greedy"],
            "matrix_mode": "fixture",
            "n_attractions": [6],
            "seed_count": 1,
            "profiles": ["relaxed"],
        },
        name="fallback_check",
    )
    scenario = build_scenarios(setup=setup, suite=suite)[0]
    non_start = scenario.problem.attractions[1:]
    assert all(a.opening_hours.open == setup.start_time + 30 for a in non_start)
    assert all(a.opening_hours.close == setup.end_time - 30 for a in non_start)


def test_tight_generates_some_precheck_feasible_cases() -> None:
    setup = setup_from_dict({}, name="baseline")
    suite = suite_from_dict(
        {
            "variants": ["astar_greedy"],
            "matrix_mode": "fixture",
            "n_attractions": [9],
            "seed_count": 8,
            "profiles": ["tight"],
        },
        name="tight_balance_check",
    )
    scenarios = build_scenarios(setup=setup, suite=suite)
    feasible = sum(
        1 for s in scenarios if scenarios_mod._is_problem_precheck_feasible(s.problem)
    )
    assert feasible > 0


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

    setup = setup_from_dict(
        {
            "profiles": ["relaxed", "tight", "impossible"],
            "n_attractions": [6, 9],
            "seed_count": 2,
        },
        name="baseline",
    )
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


def test_build_scenarios_loads_default_relative_handpicked_file() -> None:
    setup = setup_from_dict(
        {
            "profiles": ["relaxed", "tight", "impossible"],
            "n_attractions": [6, 9],
            "seed_count": 2,
        },
        name="baseline",
    )
    suite = suite_from_dict(
        {
            "variants": ["astar_greedy"],
            "matrix_mode": "fixture",
            "n_attractions": [],
            "seed_count": 0,
            "profiles": [],
            "include_handpicked": True,
        },
        name="handpicked_default",
    )

    scenarios = build_scenarios(setup=setup, suite=suite)
    assert [s.id for s in scenarios] == [
        "boundary_all_impossible",
        "boundary_single_unreachable",
        "boundary_empty_only_start",
        "boundary_timeout_bf",
    ]


def test_boundary_single_unreachable_contains_forced_unreachable_stop() -> None:
    setup = setup_from_dict(
        {
            "profiles": ["relaxed", "tight", "impossible"],
            "n_attractions": [6, 9],
            "seed_count": 2,
        },
        name="baseline",
    )
    suite = suite_from_dict(
        {
            "variants": ["astar_greedy"],
            "matrix_mode": "fixture",
            "n_attractions": [],
            "seed_count": 0,
            "profiles": [],
            "include_handpicked": True,
        },
        name="handpicked_default",
    )

    scenarios = build_scenarios(setup=setup, suite=suite)
    target = next(s for s in scenarios if s.id == "boundary_single_unreachable")
    assert target.profile == "relaxed"
    assert target.n_attractions == 6
    assert len(target.problem.attractions) == 6
    unreachable = target.problem.attractions[1]
    assert unreachable.stay.min > 0.0
    assert (
        unreachable.opening_hours.open + unreachable.stay.min
        > unreachable.opening_hours.close
    )


def test_boundary_empty_only_start_keeps_single_start_attraction() -> None:
    setup = setup_from_dict(
        {
            "profiles": ["relaxed", "tight", "impossible"],
            "n_attractions": [6, 9],
            "seed_count": 2,
        },
        name="baseline",
    )
    suite = suite_from_dict(
        {
            "variants": ["astar_greedy"],
            "matrix_mode": "fixture",
            "n_attractions": [],
            "seed_count": 0,
            "profiles": [],
            "include_handpicked": True,
        },
        name="handpicked_default",
    )

    scenarios = build_scenarios(setup=setup, suite=suite)
    target = next(s for s in scenarios if s.id == "boundary_empty_only_start")
    assert target.profile == "relaxed"
    assert target.n_attractions == 1
    assert len(target.problem.attractions) == 1
    start = target.problem.attractions[0]
    assert start.stay.min == 0.0
    assert start.stay.max == 0.0


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
    setup = setup_from_dict(
        {
            "profiles": ["relaxed", "tight", "impossible"],
            "n_attractions": [6, 9],
            "seed_count": 2,
        },
        name="baseline",
    )
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
    setup = setup_from_dict(
        {
            "profiles": ["relaxed", "tight", "impossible"],
            "n_attractions": [6, 9],
            "seed_count": 2,
        },
        name="baseline",
    )
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
