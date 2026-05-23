from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def outputs_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "outputs"


def figures_dir() -> Path:
    out = outputs_dir() / "figures"
    out.mkdir(parents=True, exist_ok=True)
    return out


def read_results() -> pd.DataFrame:
    path = outputs_dir() / "results.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def read_results_deduped() -> pd.DataFrame:
    df = read_results()
    if df.empty:
        return df
    keyed = ["experiment", "scenario_id", "mode"]
    if "timestamp_utc" in df.columns:
        parsed = pd.to_datetime(df["timestamp_utc"], errors="coerce")
        df = df.assign(_parsed_ts=parsed).sort_values("_parsed_ts")
        return df.drop_duplicates(subset=keyed, keep="last").drop(
            columns=["_parsed_ts"]
        )
    return df.drop_duplicates(subset=keyed, keep="last")


def summarize_with_iqr(
    df: pd.DataFrame, value_column: str, group_columns: list[str]
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    grouped = (
        df.groupby(group_columns)[value_column]
        .agg(
            median="median",
            q1=lambda s: s.quantile(0.25),
            q3=lambda s: s.quantile(0.75),
            count="count",
        )
        .reset_index()
    )
    grouped["iqr_low"] = (grouped["median"] - grouped["q1"]).clip(lower=0.0)
    grouped["iqr_high"] = (grouped["q3"] - grouped["median"]).clip(lower=0.0)
    return grouped


def save_fig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(figures_dir() / name, dpi=150)
    plt.close()
