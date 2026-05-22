from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .metrics import _enrich_results
from .types import Row


def output_dir_default() -> Path:
    return Path(__file__).resolve().parents[2] / "outputs"


def _write_outputs(*, output_dir: Path, rows: list[Row]) -> pd.DataFrame:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "raw").mkdir(parents=True, exist_ok=True)

    rows_dict = [asdict(row) for row in rows]
    raw_df = pd.DataFrame(rows_dict)
    df = _enrich_results(raw_df) if not raw_df.empty else raw_df

    if not df.empty:
        df.to_csv(output_dir / "results.csv", index=False)
        agg = (
            df.groupby(["experiment", "n_attractions", "profile", "mode"], dropna=False)
            .agg(
                run_count=("experiment", "count"),
                ok_count=("status", lambda s: int((s == "ok").sum())),
                wall_time_ms_mean=("wall_time_ms", "mean"),
                wall_time_ms_std=("wall_time_ms", "std"),
                expanded_nodes_mean=("expanded_nodes", "mean"),
                objective_cost_median=("objective_cost", "median"),
                peak_memory_mb_mean=("peak_memory_mb", "mean"),
                optimality_gap_mean=("optimality_gap", "mean"),
                stay_utilization_mean=("stay_utilization", "mean"),
            )
            .reset_index()
        )
        agg.to_csv(output_dir / "aggregated.csv", index=False)
    else:
        with (output_dir / "results.csv").open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(Row.__annotations__.keys())
        with (output_dir / "aggregated.csv").open(
            "w", encoding="utf-8", newline=""
        ) as fh:
            writer = csv.writer(fh)
            writer.writerow(["experiment", "n_attractions", "profile", "mode"])

    with (output_dir / "raw" / "results.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows_dict:
            fh.write(json.dumps(row) + "\n")
    return df
