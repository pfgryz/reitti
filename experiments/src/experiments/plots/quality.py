from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from .common import read_results_deduped, save_fig


def prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    part = df[
        (df["mode"] == "fixture")
        & (df["status"] == "ok")
        & (df["suite"] != "handpicked_validation")
    ]
    profiles = [p for p in ["relaxed", "tight"] if p in set(part["profile"])]
    if not profiles:
        profiles = sorted(part["profile"].dropna().unique())
    return part, profiles


def render(part: pd.DataFrame, profiles: list[str]) -> None:
    if part.empty:
        return
    if not profiles:
        return
    fig, axes = plt.subplots(
        1, len(profiles), figsize=(7 * len(profiles), 5), sharey=False
    )
    if len(profiles) == 1:
        axes = [axes]
    for ax, profile in zip(axes, profiles):
        p = part[part["profile"] == profile]
        if p.empty:
            continue
        experiments = sorted(p["experiment"].unique())
        data = [
            p[p["experiment"] == exp]["objective_cost"].dropna().values
            for exp in experiments
        ]
        ax.boxplot(data, tick_labels=experiments)
        ax.tick_params(axis="x", labelrotation=20)
        ax.set_title(f"{profile} profile")
        ax.grid(alpha=0.2, axis="y")
    axes[0].set_ylabel("objective_cost")
    fig.suptitle("Quality distribution by algorithm (fixture)")
    save_fig("quality_boxplot.png")


def main() -> None:
    part, profiles = prepare(read_results_deduped())
    render(part, profiles)


if __name__ == "__main__":
    main()
