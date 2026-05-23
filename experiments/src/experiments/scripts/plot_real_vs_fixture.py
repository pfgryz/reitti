from __future__ import annotations

import matplotlib.pyplot as plt

from .common import (
    detect_latest_real_vs_fixture_pair,
    read_results_deduped,
    save_fig,
    summarize_with_iqr,
)


def main() -> None:
    df = read_results_deduped()
    pair = detect_latest_real_vs_fixture_pair(df)
    if pair is None:
        return
    fixture_prefix, real_prefix = pair
    part = df[
        (df["experiment"].isin(["astar_greedy", "astar_intervals"]))
        & (df["status"] == "ok")
        & (df["profile"] == "relaxed")
        & (
            ((df["mode"] == "fixture") & (df["scenario_id"].str.startswith(fixture_prefix, na=False)))
            | ((df["mode"] == "real") & (df["scenario_id"].str.startswith(real_prefix, na=False)))
        )
    ]
    if part.empty:
        return
    experiments = sorted(part["experiment"].unique())
    fig, axes = plt.subplots(1, len(experiments), figsize=(7 * len(experiments), 5), sharey=True)
    if len(experiments) == 1:
        axes = [axes]

    for ax, experiment in zip(axes, experiments):
        p = part[part["experiment"] == experiment]
        summary = summarize_with_iqr(p, "wall_time_ms", ["mode", "n_attractions"])
        for mode in ["fixture", "real"]:
            s = summary[summary["mode"] == mode].sort_values("n_attractions")
            if s.empty:
                continue
            ax.errorbar(
                s["n_attractions"],
                s["median"],
                yerr=[s["iqr_low"], s["iqr_high"]],
                marker="o",
                capsize=3,
                label=mode,
            )
        ax.set_xlabel("n_attractions")
        ax.set_title(experiment)
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("wall_time_ms (median, IQR)")
    axes[-1].legend()
    fig.suptitle("Real vs fixture runtime (aligned relaxed suites)")
    save_fig("real_vs_fixture.png")


if __name__ == "__main__":
    main()
