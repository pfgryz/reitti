from __future__ import annotations

import pandas as pd
import pytest

from experiments.metrics.speedup import add_heuristic_speedup


def test_add_heuristic_speedup_docstring_mentions_derived_columns() -> None:
    doc = add_heuristic_speedup.__doc__
    assert doc is not None
    assert "heuristic_speedup" in doc
    assert "wall_time_ms" in doc
    assert "t_no_h / t_h" in doc


def test_add_heuristic_speedup_uses_matched_rows() -> None:
    df = pd.DataFrame(
        [
            {
                "experiment": "astar_intervals",
                "scenario_id": "s1",
                "mode": "fixture",
                "status": "ok",
                "wall_time_ms": 100.0,
            },
            {
                "experiment": "astar_intervals_no_heuristic",
                "scenario_id": "s1",
                "mode": "fixture",
                "status": "ok",
                "wall_time_ms": 200.0,
            },
        ]
    )
    out = add_heuristic_speedup(df)
    speedup = float(out["heuristic_speedup"].dropna().iloc[0])
    assert speedup == pytest.approx(2.0)
