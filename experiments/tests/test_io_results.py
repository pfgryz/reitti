from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.io_results import _write_outputs
from experiments.types import Row


def _row(*, suite: str, mode: str, scenario_id: str, ts: str) -> Row:
    return Row(
        experiment="astar_greedy",
        scenario_id=scenario_id,
        profile="relaxed",
        suite=suite,
        setup_name="baseline",
        stay_mode="greedy",
        mode=mode,
        data_source="fixture_synthetic" if mode == "fixture" else "graphhopper_gtfs",
        status="ok",
        n_attractions=6,
        wall_time_ms=10.0,
        peak_memory_mb=1.0,
        expanded_nodes=10,
        generated_nodes=20,
        pruned_by_best_g=0,
        visits_count=5,
        total_stay_minutes=100.0,
        stay_utilization=1.0,
        total_walk_distance_m=1000.0,
        objective_cost=1000.0,
        bf_objective=None,
        optimality_gap=None,
        heuristic_speedup=None,
        feasibility_correctness=None,
        end_time=1000.0,
        seed=1,
        error=None,
        timestamp_utc=ts,
    )


def test_write_outputs_appends_across_runs(tmp_path: Path) -> None:
    _write_outputs(
        output_dir=tmp_path,
        rows=[
            _row(
                suite="synthetic_main",
                mode="fixture",
                scenario_id="s1",
                ts="2026-01-01T00:00:00+00:00",
            )
        ],
    )
    _write_outputs(
        output_dir=tmp_path,
        rows=[
            _row(
                suite="real_reference",
                mode="real",
                scenario_id="s2",
                ts="2026-01-01T00:01:00+00:00",
            )
        ],
    )

    out = pd.read_csv(tmp_path / "results.csv")
    assert set(out["suite"]) == {"synthetic_main", "real_reference"}
    assert len(out) == 2
