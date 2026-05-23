from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from .common import read_results_deduped, save_fig, summarize_with_iqr


def prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    part = df[
        (df["suite"] == "heuristic_ablation")
        & (df["mode"] == "fixture")
        & (df["status"] == "ok")
        & (df["experiment"].isin(["astar_intervals", "astar_intervals_no_heuristic"]))
    ]
    profiles = [p for p in ["relaxed", "tight"] if p in set(part["profile"])]
    if not profiles:
        profiles = sorted(part["profile"].dropna().unique())
    return part, profiles


def render(part: pd.DataFrame, profiles: list[str]) -> None:
    if part.empty or not profiles:
        return
    fig, axes = plt.subplots(
        1, len(profiles), figsize=(7 * len(profiles), 5), sharey=True
    )
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
    fig.suptitle("Heuristic ablation runtime (fixture)")
    save_fig("heuristic_ablation.png")


def main() -> None:
    part, profiles = prepare(read_results_deduped())
    render(part, profiles)


if __name__ == "__main__":
    main()
