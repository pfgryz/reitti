from __future__ import annotations

import pandas as pd
import pytest

from experiments.plots import (
    ablation,
    expanded_nodes,
    feasibility,
    gap,
    memory,
    quality,
    runtime,
)


def _shared_plot_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "row_id": "keep_boundary_synthetic",
                "suite": "synthetic_main",
                "mode": "fixture",
                "status": "ok",
                "scenario_id": "boundary_case_should_now_be_kept",
                "profile": "relaxed",
                "experiment": "astar_greedy",
                "peak_memory_mb": 128.0,
            },
            {
                "row_id": "drop_handpicked",
                "suite": "handpicked_validation",
                "mode": "fixture",
                "status": "ok",
                "scenario_id": "plain_fixture_case",
                "profile": "tight",
                "experiment": "astar_intervals",
                "peak_memory_mb": 64.0,
            },
            {
                "row_id": "drop_real_mode",
                "suite": "synthetic_main",
                "mode": "real",
                "status": "ok",
                "scenario_id": "plain_real_case",
                "profile": "relaxed",
                "experiment": "astar_greedy",
                "peak_memory_mb": 32.0,
            },
            {
                "row_id": "drop_non_ok_status",
                "suite": "synthetic_main",
                "mode": "fixture",
                "status": "infeasible",
                "scenario_id": "plain_infeasible_case",
                "profile": "relaxed",
                "experiment": "astar_greedy",
                "peak_memory_mb": 16.0,
            },
            {
                "row_id": "drop_missing_memory",
                "suite": "synthetic_main",
                "mode": "fixture",
                "status": "ok",
                "scenario_id": "plain_missing_memory_case",
                "profile": "relaxed",
                "experiment": "astar_greedy",
                "peak_memory_mb": None,
            },
        ]
    )


def _feasibility_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "row_id": "keep_handpicked_fixture",
                "suite": "handpicked_validation",
                "experiment": "astar_intervals",
                "scenario_id": "not_boundary_anymore",
                "mode": "fixture",
                "status": "ok",
            },
            {
                "row_id": "keep_handpicked_real",
                "suite": "handpicked_validation",
                "experiment": "astar_intervals",
                "scenario_id": "another_regular_case",
                "mode": "real",
                "status": "timeout",
            },
            {
                "row_id": "drop_wrong_suite",
                "suite": "synthetic_main",
                "experiment": "astar_intervals",
                "scenario_id": "not_boundary_wrong_suite",
                "mode": "fixture",
                "status": "ok",
            },
            {
                "row_id": "drop_wrong_experiment",
                "suite": "handpicked_validation",
                "experiment": "astar_greedy",
                "scenario_id": "not_boundary_wrong_exp",
                "mode": "fixture",
                "status": "ok",
            },
        ]
    )


def test_runtime_prepare_excludes_handpicked_suite() -> None:
    base, profiles = runtime.prepare(_shared_plot_df())
    assert set(base["row_id"]) == {"keep_boundary_synthetic", "drop_missing_memory"}
    assert profiles == ["relaxed"]


def test_expanded_nodes_prepare_excludes_handpicked_suite() -> None:
    base, profiles = expanded_nodes.prepare(_shared_plot_df())
    assert set(base["row_id"]) == {"keep_boundary_synthetic", "drop_missing_memory"}
    assert profiles == ["relaxed"]


def test_quality_prepare_excludes_handpicked_suite() -> None:
    part, profiles = quality.prepare(_shared_plot_df())
    assert set(part["row_id"]) == {"keep_boundary_synthetic", "drop_missing_memory"}
    assert profiles == ["relaxed"]


def test_memory_prepare_excludes_handpicked_and_missing_memory() -> None:
    base, profiles = memory.prepare(_shared_plot_df())
    assert set(base["row_id"]) == {"keep_boundary_synthetic"}
    assert profiles == ["relaxed"]


def test_feasibility_prepare_uses_suite_and_experiment_semantics() -> None:
    part = feasibility.prepare(_feasibility_df())
    assert set(part["row_id"]) == {"keep_handpicked_fixture", "keep_handpicked_real"}


def test_ablation_prepare_constrains_heuristic_ablation_suite() -> None:
    df = pd.DataFrame(
        [
            {
                "row_id": "keep_right_suite",
                "suite": "heuristic_ablation",
                "mode": "fixture",
                "status": "ok",
                "profile": "relaxed",
                "experiment": "astar_intervals",
                "wall_time_ms": 10.0,
            },
            {
                "row_id": "drop_wrong_suite",
                "suite": "synthetic_main",
                "mode": "fixture",
                "status": "ok",
                "profile": "tight",
                "experiment": "astar_intervals_no_heuristic",
                "wall_time_ms": 12.0,
            },
        ]
    )
    part, profiles = ablation.prepare(df)
    assert set(part["row_id"]) == {"keep_right_suite"}
    assert profiles == ["relaxed"]


def test_gap_prepare_constrains_bf_reference_small_n_suite() -> None:
    df = pd.DataFrame(
        [
            {
                "row_id": "keep_right_suite",
                "suite": "bf_reference_small_n",
                "mode": "fixture",
                "status": "ok",
                "profile": "tight",
                "experiment": "astar_greedy",
                "optimality_gap": 0.1,
            },
            {
                "row_id": "drop_wrong_suite",
                "suite": "synthetic_main",
                "mode": "fixture",
                "status": "ok",
                "profile": "relaxed",
                "experiment": "astar_intervals",
                "optimality_gap": 0.2,
            },
        ]
    )
    part, profiles = gap.prepare(df)
    assert set(part["row_id"]) == {"keep_right_suite"}
    assert profiles == ["tight"]


@pytest.mark.parametrize(
    ("module", "metric_column"),
    [
        (runtime, "wall_time_ms"),
        (expanded_nodes, "expanded_nodes"),
        (memory, "peak_memory_mb"),
        (quality, "objective_cost"),
        (gap, "optimality_gap"),
        (ablation, "wall_time_ms"),
    ],
)
def test_render_ignores_empty_profile_categories(
    module, metric_column, monkeypatch
) -> None:
    monkeypatch.setattr(module, "save_fig", lambda *_args, **_kwargs: None)
    base = pd.DataFrame(
        [
            {
                "profile": "relaxed",
                "experiment": "astar_greedy",
                "n_attractions": 5,
                metric_column: 1.0,
            }
        ]
    )
    module.render(base, [])


def test_feasibility_render_ignores_empty_mode_categories(monkeypatch) -> None:
    monkeypatch.setattr(feasibility, "save_fig", lambda *_args, **_kwargs: None)
    part = pd.DataFrame(
        [
            {
                "profile": "relaxed",
                "status": "ok",
                "mode": "shadow",
            }
        ]
    )
    feasibility.render(part)


def test_runtime_render_single_profile_sanity(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "save_fig", lambda *_args, **_kwargs: None)
    base = pd.DataFrame(
        [
            {
                "profile": "relaxed",
                "experiment": "astar_greedy",
                "n_attractions": 5,
                "wall_time_ms": 100.0,
            }
        ]
    )
    runtime.render(base, ["relaxed"])
