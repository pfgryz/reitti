from __future__ import annotations

import pandas as pd

from experiments.plots import common


def test_outputs_dir_points_to_project_outputs() -> None:
    out = common.outputs_dir()
    assert out.name == "outputs"
    assert out.parent.name == "experiments"


def test_read_results_deduped_keeps_latest_row(monkeypatch, tmp_path) -> None:
    data = pd.DataFrame(
        [
            {
                "experiment": "astar_greedy",
                "scenario_id": "s1",
                "mode": "fixture",
                "wall_time_ms": 10.0,
                "timestamp_utc": "2026-01-01T00:00:00+00:00",
            },
            {
                "experiment": "astar_greedy",
                "scenario_id": "s1",
                "mode": "fixture",
                "wall_time_ms": 20.0,
                "timestamp_utc": "2026-01-01T00:01:00+00:00",
            },
        ]
    )
    data.to_csv(tmp_path / "results.csv", index=False)
    monkeypatch.setattr(common, "outputs_dir", lambda: tmp_path)
    out = common.read_results_deduped()
    assert len(out) == 1
    assert float(out.iloc[0]["wall_time_ms"]) == 20.0
