from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .metrics import enrich_results
from .types import Row


def output_dir_default() -> Path:
    return Path(__file__).resolve().parents[2] / "outputs"


def _write_outputs(*, output_dir: Path, rows: list[Row]) -> pd.DataFrame:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "raw").mkdir(parents=True, exist_ok=True)

    raw_columns = list(Row.__annotations__.keys())
    rows_dict = [asdict(row) for row in rows]
    raw_df = pd.DataFrame(rows_dict)
    existing_path = output_dir / "results.csv"
    if existing_path.exists():
        existing_df = pd.read_csv(existing_path)
        if not existing_df.empty:
            existing_raw = existing_df.reindex(columns=raw_columns)
            raw_df = pd.concat([existing_raw, raw_df], ignore_index=True)

    df = enrich_results(raw_df) if not raw_df.empty else raw_df

    if not df.empty:
        if "timestamp_utc" in df.columns:
            parsed = pd.to_datetime(df["timestamp_utc"], errors="coerce")
            df = (
                df.assign(_parsed_ts=parsed)
                .sort_values("_parsed_ts")
                .drop_duplicates(
                    subset=["experiment", "scenario_id", "mode"], keep="last"
                )
                .drop(columns=["_parsed_ts"])
            )
        df.to_csv(output_dir / "results.csv", index=False)
        agg = (
            df.groupby(
                [
                    "experiment",
                    "n_attractions",
                    "profile",
                    "suite",
                    "setup_name",
                    "mode",
                ],
                dropna=False,
            )
            .agg(
                run_count=("experiment", "count"),
                ok_count=("status", lambda s: int((s == "ok").sum())),
                timeout_count=("status", lambda s: int((s == "timeout").sum())),
                timeout_rate=("status", lambda s: float((s == "timeout").mean())),
                wall_time_ms_mean=(
                    "wall_time_ms",
                    lambda s: s[df.loc[s.index, "status"] == "ok"].mean(),
                ),
                wall_time_ms_std=(
                    "wall_time_ms",
                    lambda s: s[df.loc[s.index, "status"] == "ok"].std(),
                ),
                expanded_nodes_mean=(
                    "expanded_nodes",
                    lambda s: s[df.loc[s.index, "status"] == "ok"].mean(),
                ),
                objective_cost_median=(
                    "objective_cost",
                    lambda s: s[df.loc[s.index, "status"] == "ok"].median(),
                ),
                peak_memory_mb_mean=(
                    "peak_memory_mb",
                    lambda s: s[df.loc[s.index, "status"] == "ok"].mean(),
                ),
                optimality_gap_mean=("optimality_gap", "mean"),
                stay_utilization_mean=(
                    "stay_utilization",
                    lambda s: s[df.loc[s.index, "status"] == "ok"].mean(),
                ),
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
            writer.writerow(
                [
                    "experiment",
                    "n_attractions",
                    "profile",
                    "suite",
                    "setup_name",
                    "mode",
                ]
            )

    with (output_dir / "raw" / "results.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows_dict:
            fh.write(json.dumps(row) + "\n")
    return df
