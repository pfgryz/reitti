from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from .common import read_results_deduped, save_fig, summarize_with_iqr


def prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    base = df[
        (df["mode"] == "fixture")
        & (df["status"] == "ok")
        & (df["peak_memory_mb"].notna())
        & (df["suite"] != "handpicked_validation")
    ]
    profiles = [p for p in ["relaxed", "tight"] if p in set(base["profile"])]
    if not profiles:
        profiles = sorted(base["profile"].dropna().unique())
    return base, profiles


def render(base: pd.DataFrame, profiles: list[str]) -> None:
    if base.empty:
        return
    if not profiles:
        return
    fig, axes = plt.subplots(
        1, len(profiles), figsize=(7 * len(profiles), 5), sharey=True
    )
    if len(profiles) == 1:
        axes = [axes]
    for ax, profile in zip(axes, profiles):
        part = base[base["profile"] == profile]
        if part.empty:
            continue
        summary = summarize_with_iqr(
            part, "peak_memory_mb", ["experiment", "n_attractions"]
        )
        for experiment in sorted(summary["experiment"].unique()):
            s = summary[summary["experiment"] == experiment].sort_values(
                "n_attractions"
            )
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
    fig.suptitle("Memory scaling (fixture)")
    save_fig("memory_scaling.png")


def main() -> None:
    base, profiles = prepare(read_results_deduped())
    render(base, profiles)


if __name__ == "__main__":
    main()
