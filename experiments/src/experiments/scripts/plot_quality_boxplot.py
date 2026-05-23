from __future__ import annotations

import matplotlib.pyplot as plt

from .common import (
    detect_latest_fixture_suite_family,
    prefixes_for_suite_family,
    read_results_deduped,
    save_fig,
)


def main() -> None:
    df = read_results_deduped()
    suite_family = detect_latest_fixture_suite_family(df)
    if suite_family is None:
        return
    astar_prefix, bf_prefix = prefixes_for_suite_family(suite_family)
    part = df[
        (df["mode"] == "fixture")
        & (df["status"] == "ok")
        & (
            df["scenario_id"].str.startswith(astar_prefix, na=False)
            | df["scenario_id"].str.startswith(bf_prefix, na=False)
        )
        & (~df["scenario_id"].str.startswith("boundary_", na=False))
    ]
    if part.empty:
        return
    profiles = [p for p in ["relaxed", "tight"] if p in set(part["profile"])]
    if not profiles:
        profiles = sorted(part["profile"].dropna().unique())
    fig, axes = plt.subplots(1, len(profiles), figsize=(7 * len(profiles), 5), sharey=False)
    if len(profiles) == 1:
        axes = [axes]

    for ax, profile in zip(axes, profiles):
        p = part[part["profile"] == profile]
        if p.empty:
            continue
        exps = sorted(p["experiment"].unique())
        data = [p[p["experiment"] == e]["objective_cost"].dropna().values for e in exps]
        ax.boxplot(data, tick_labels=exps)
        ax.tick_params(axis="x", labelrotation=20)
        ax.set_title(f"{profile} profile")
        ax.grid(alpha=0.2, axis="y")
    axes[0].set_ylabel("objective_cost")
    fig.suptitle("Quality distribution by algorithm (fixture fast suites)")
    save_fig("quality_boxplot.png")


if __name__ == "__main__":
    main()
