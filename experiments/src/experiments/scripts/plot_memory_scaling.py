from __future__ import annotations

import matplotlib.pyplot as plt

from .common import (
    detect_latest_fixture_suite_family,
    prefixes_for_suite_family,
    read_results_deduped,
    save_fig,
    summarize_with_iqr,
)


def _canonical_scaling_subset(df):
    suite_family = detect_latest_fixture_suite_family(df)
    if suite_family is None:
        return df.iloc[0:0]
    astar_prefix, bf_prefix = prefixes_for_suite_family(suite_family)
    astar_like = df["experiment"].isin(["astar_greedy", "astar_intervals"])
    bf_like = df["experiment"].isin(
        ["astar_intervals_no_heuristic", "bruteforce_greedy", "bruteforce_intervals"]
    )
    from_astar_suite = df["scenario_id"].str.startswith(astar_prefix, na=False)
    from_bf_suite = df["scenario_id"].str.startswith(bf_prefix, na=False)
    return df[(astar_like & from_astar_suite) | (bf_like & from_bf_suite)]


def main() -> None:
    df = read_results_deduped()
    if df.empty:
        return
    base = df[
        (df["mode"] == "fixture")
        & (df["status"] == "ok")
        & (df["peak_memory_mb"].notna())
        & (~df["scenario_id"].str.startswith("boundary_", na=False))
    ]
    base = _canonical_scaling_subset(base)
    if base.empty:
        return
    profiles = [p for p in ["relaxed", "tight"] if p in set(base["profile"])]
    if not profiles:
        profiles = sorted(base["profile"].dropna().unique())

    fig, axes = plt.subplots(1, len(profiles), figsize=(7 * len(profiles), 5), sharey=True)
    if len(profiles) == 1:
        axes = [axes]

    for ax, profile in zip(axes, profiles):
        part = base[base["profile"] == profile]
        if part.empty:
            continue
        summary = summarize_with_iqr(part, "peak_memory_mb", ["experiment", "n_attractions"])
        for experiment in sorted(summary["experiment"].unique()):
            s = summary[summary["experiment"] == experiment].sort_values("n_attractions")
            ax.errorbar(
                s["n_attractions"],
                s["median"],
                yerr=[s["iqr_low"], s["iqr_high"]],
                marker="o",
                capsize=3,
                label=experiment,
            )
        ax.set_xlabel("n_attractions")
        ax.set_title(f"{profile} profile")
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("peak_memory_mb (median, IQR)")
    axes[-1].legend()
    fig.suptitle("Memory scaling (fixture, canonical suites)")
    save_fig("memory_scaling.png")


if __name__ == "__main__":
    main()
