from __future__ import annotations

import pandas as pd

from experiments.metrics.feasibility import add_feasibility_correctness


def test_add_feasibility_correctness_docstring_mentions_derived_columns() -> None:
    doc = add_feasibility_correctness.__doc__
    assert doc is not None
    assert "feasibility_correctness" in doc
    assert "status" in doc
    assert "expected_status" in doc


def test_add_feasibility_correctness_sets_boundary_flags() -> None:
    df = pd.DataFrame(
        [
            {
                "experiment": "astar_intervals",
                "scenario_id": "boundary_all_impossible",
                "profile": "impossible",
                "status": "infeasible",
            },
            {
                "experiment": "bruteforce_greedy",
                "scenario_id": "boundary_timeout_bf",
                "profile": "relaxed",
                "status": "timeout",
            },
        ]
    )
    out = add_feasibility_correctness(df)
    assert bool(out.loc[0, "feasibility_correctness"]) is True
    assert bool(out.loc[1, "feasibility_correctness"]) is True
