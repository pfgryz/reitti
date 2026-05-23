from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from experiments.metrics import enrich_results


def _experiments_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _parse_args() -> argparse.Namespace:
    root = _experiments_root()
    parser = argparse.ArgumentParser(
        description="Merge suite shard outputs into outputs/results.csv and outputs/aggregated.csv."
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=root / "outputs" / "runs",
        help="Directory containing shard folders with results.csv files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=root / "outputs",
        help="Directory where merged results.csv and aggregated.csv are written.",
    )
    return parser.parse_args()


def _load_shards(input_root: Path) -> tuple[pd.DataFrame, int]:
    shard_paths = sorted(input_root.glob("*/results.csv"))
    if not shard_paths:
        raise FileNotFoundError(
            f"No shard files found under '{input_root}' (expected pattern: */results.csv)."
        )

    frames = [pd.read_csv(path) for path in shard_paths]
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return merged, len(shard_paths)


def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    keys = ["experiment", "scenario_id", "mode"]
    if "timestamp_utc" in df.columns:
        parsed = pd.to_datetime(df["timestamp_utc"], errors="coerce")
        return (
            df.assign(_parsed_ts=parsed, _row_order=range(len(df)))
            .sort_values(["_parsed_ts", "_row_order"], na_position="first")
            .drop_duplicates(subset=keys, keep="last")
            .drop(columns=["_parsed_ts", "_row_order"])
        )
    return df.drop_duplicates(subset=keys, keep="last")


def _write_aggregated(df: pd.DataFrame, output_dir: Path) -> None:
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


def main() -> int:
    args = _parse_args()
    input_root = args.input_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        merged_raw, shard_count = _load_shards(input_root)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    merged = _deduplicate(merged_raw)
    merged = enrich_results(merged) if not merged.empty else merged

    merged.to_csv(output_dir / "results.csv", index=False)
    _write_aggregated(merged, output_dir)

    print(
        "[OK] merged "
        f"{shard_count} shard(s), "
        f"{len(merged_raw)} input row(s), "
        f"{len(merged)} deduplicated row(s)"
    )
    print(f"[OK] wrote {output_dir / 'results.csv'}")
    print(f"[OK] wrote {output_dir / 'aggregated.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
