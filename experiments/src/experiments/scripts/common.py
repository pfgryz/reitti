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
    return pd.read_csv(outputs_dir() / "results.csv")


def read_results_deduped() -> pd.DataFrame:
    """Read results and keep the latest row per unique run key."""
    df = read_results()
    if df.empty:
        return df
    keyed = ["experiment", "scenario_id", "mode"]
    if "timestamp_utc" in df.columns:
        parsed = pd.to_datetime(df["timestamp_utc"], errors="coerce")
        df = df.assign(_parsed_ts=parsed).sort_values("_parsed_ts")
        deduped = df.drop_duplicates(subset=keyed, keep="last").drop(
            columns=["_parsed_ts"]
        )
        return deduped
    return df.drop_duplicates(subset=keyed, keep="last")


def read_aggregated() -> pd.DataFrame:
    return pd.read_csv(outputs_dir() / "aggregated.csv")


def summarize_with_iqr(df: pd.DataFrame, value_column: str, group_columns: list[str]) -> pd.DataFrame:
    """Median + IQR summary suitable for noisy benchmark plots."""
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


def _suite_family_for_scenario_id(scenario_id: str) -> str | None:
    if scenario_id.startswith("fast_"):
        return "fast"
    if scenario_id.startswith("grid_"):
        return "full"
    return None


def detect_latest_fixture_suite_family(df: pd.DataFrame) -> str | None:
    """Pick the most recently written fixture suite family: fast or full."""
    if df.empty:
        return None
    fixture = df[df["mode"] == "fixture"].copy()
    if fixture.empty:
        return None
    fixture["suite_family"] = fixture["scenario_id"].astype(str).map(_suite_family_for_scenario_id)
    fixture = fixture[fixture["suite_family"].notna()]
    if fixture.empty:
        return None
    if "timestamp_utc" in fixture.columns:
        fixture["_ts"] = pd.to_datetime(fixture["timestamp_utc"], errors="coerce")
        newest = fixture.groupby("suite_family")["_ts"].max().dropna()
        if not newest.empty:
            return str(newest.idxmax())
    counts = fixture["suite_family"].value_counts()
    if counts.empty:
        return None
    return str(counts.index[0])


def prefixes_for_suite_family(suite_family: str) -> tuple[str, str]:
    """Return (astar_prefix, bf_prefix) for suite family."""
    if suite_family == "full":
        return ("grid_astar_", "grid_bf_")
    return ("fast_astar_", "fast_bf_")


def detect_latest_real_vs_fixture_pair(df: pd.DataFrame) -> tuple[str, str] | None:
    """
    Return the active (fixture_prefix, real_prefix) pair.

    Supported pairs:
    - fast profile: fixture=fast_astar_, real=real_relaxed_
    - full profile: fixture=grid_astar_, real=grid_astar_
    """
    if df.empty:
        return None
    candidates = [
        ("fast_astar_", "real_relaxed_"),
        ("grid_astar_", "grid_astar_"),
    ]
    best_pair: tuple[str, str] | None = None
    best_ts = None
    for fixture_prefix, real_prefix in candidates:
        fixture_mask = (df["mode"] == "fixture") & (
            df["scenario_id"].str.startswith(fixture_prefix, na=False)
        )
        real_mask = (df["mode"] == "real") & (
            df["scenario_id"].str.startswith(real_prefix, na=False)
        )
        if not fixture_mask.any() or not real_mask.any():
            continue
        if "timestamp_utc" in df.columns:
            ts = pd.to_datetime(df[fixture_mask | real_mask]["timestamp_utc"], errors="coerce").max()
            if best_ts is None or (pd.notna(ts) and ts > best_ts):
                best_ts = ts
                best_pair = (fixture_prefix, real_prefix)
        elif best_pair is None:
            best_pair = (fixture_prefix, real_prefix)
    return best_pair


def save_fig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(figures_dir() / name, dpi=150)
    plt.close()
