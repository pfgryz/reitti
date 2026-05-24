from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROFILE_PL = {"relaxed": "swobodny", "tight": "wymagający"}


def profile_label_pl(profile: str) -> str:
    return f"profil {PROFILE_PL.get(profile, profile)}"


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


def fixture_ok_rate(df: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    """Compute ok_count / run_count per group on the same pre-filter the
    fixture plots use (fixture mode, non handpicked validation suite).

    Used to fade markers and annotate timeouts on scaling plots so the
    'survivor bias' near the timeout boundary is visible.
    """
    if df.empty:
        return pd.DataFrame(columns=[*group_columns, "run_count", "ok_count", "ok_rate"])
    base = df[(df["mode"] == "fixture") & (df["suite"] != "handpicked_validation")]
    if base.empty:
        return pd.DataFrame(columns=[*group_columns, "run_count", "ok_count", "ok_rate"])
    grouped = (
        base.groupby(group_columns, dropna=False)
        .agg(
            run_count=("status", "count"),
            ok_count=("status", lambda s: int((s == "ok").sum())),
        )
        .reset_index()
    )
    denom = grouped["run_count"].where(grouped["run_count"] > 0, 1)
    grouped["ok_rate"] = grouped["ok_count"] / denom
    return grouped


def annotate_partial_completion(
    ax,
    summary: pd.DataFrame,
    rate_table: pd.DataFrame,
    *,
    join_columns: list[str],
    x_column: str = "n_attractions",
    y_column: str = "median",
) -> pd.DataFrame:
    """Merge ok_rate into summary so callers can fade markers, and annotate
    points where ok_rate < 1 with 'ok/total' next to the marker.

    Returns the merged DataFrame so callers can iterate it for plotting.
    """
    if summary.empty:
        return summary
    if rate_table.empty:
        merged = summary.copy()
        merged["ok_rate"] = 1.0
        merged["ok_count"] = merged.get("count", 0)
        merged["run_count"] = merged.get("count", 0)
        return merged
    merged = summary.merge(
        rate_table[[*join_columns, "ok_count", "run_count", "ok_rate"]],
        on=join_columns,
        how="left",
    )
    merged["ok_rate"] = merged["ok_rate"].fillna(1.0).clip(lower=0.0, upper=1.0)
    for _, row in merged.iterrows():
        if pd.isna(row[y_column]):
            continue
        if row["ok_rate"] >= 1.0:
            continue
        if pd.isna(row.get("ok_count")) or pd.isna(row.get("run_count")):
            continue
        ax.annotate(
            f"{int(row['ok_count'])}/{int(row['run_count'])}",
            xy=(row[x_column], row[y_column]),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=7,
            color="#444",
        )
    return merged
