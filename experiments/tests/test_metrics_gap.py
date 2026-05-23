from __future__ import annotations

import pandas as pd
import pytest

from experiments.metrics.gap import add_optimality_gap


def test_add_optimality_gap_docstring_mentions_derived_columns() -> None:
    doc = add_optimality_gap.__doc__
    assert doc is not None
    assert "bf_objective" in doc
    assert "optimality_gap" in doc
    assert "objective_cost" in doc


def test_add_optimality_gap_matches_bf_rows() -> None:
    df = pd.DataFrame(
        [
            {
                "experiment": "astar_greedy",
                "scenario_id": "s1",
                "mode": "fixture",
                "stay_mode": "greedy",
                "status": "ok",
                "objective_cost": 2000.0,
            },
            {
                "experiment": "bruteforce_greedy",
                "scenario_id": "s1",
                "mode": "fixture",
                "stay_mode": "greedy",
                "status": "ok",
                "objective_cost": 1800.0,
            },
        ]
    )
    out = add_optimality_gap(df)
    gap = float(out[out["experiment"] == "astar_greedy"]["optimality_gap"].iloc[0])
    assert gap == pytest.approx((2000.0 - 1800.0) / 1800.0)
