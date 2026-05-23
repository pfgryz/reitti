from __future__ import annotations

import matplotlib.pyplot as plt

from .common import (
    detect_latest_fixture_suite_family,
    prefixes_for_suite_family,
    read_results_deduped,
    save_fig,
    summarize_with_iqr,
)


def main() -> None:
    df = read_results_deduped()
    suite_family = detect_latest_fixture_suite_family(df)
    if suite_family is None:
        return
    _, bf_prefix = prefixes_for_suite_family(suite_family)
    part = df[
        (df["mode"] == "fixture")
        & (df["scenario_id"].str.startswith(bf_prefix, na=False))
        & (df["experiment"].isin(["astar_intervals", "astar_intervals_no_heuristic"]))
        & (df["status"] == "ok")
    ]
    if part.empty:
        return
    profiles = [p for p in ["relaxed", "tight"] if p in set(part["profile"])]
    if not profiles:
        profiles = sorted(part["profile"].dropna().unique())
    fig, axes = plt.subplots(1, len(profiles), figsize=(7 * len(profiles), 5), sharey=True)
    if len(profiles) == 1:
        axes = [axes]

    for ax, profile in zip(axes, profiles):
        p = part[part["profile"] == profile]
        if p.empty:
            continue
        summary = summarize_with_iqr(p, "wall_time_ms", ["experiment", "n_attractions"])
        for exp in sorted(summary["experiment"].unique()):
            s = summary[summary["experiment"] == exp].sort_values("n_attractions")
            ax.errorbar(
                s["n_attractions"],
                s["median"],
                yerr=[s["iqr_low"], s["iqr_high"]],
                marker="o",
                capsize=3,
                label=exp,
            )
        ax.set_xlabel("n_attractions")
        ax.set_title(f"{profile} profile")
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("wall_time_ms (median, IQR)")
    axes[-1].legend()
    fig.suptitle("Heuristic ablation runtime (fixture fast_bf suite)")
    save_fig("heuristic_ablation.png")


if __name__ == "__main__":
    main()
