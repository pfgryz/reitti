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
        & (df["status"] == "ok")
        & (df["experiment"].str.startswith("astar"))
        & (df["optimality_gap"].notna())
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
        summary = summarize_with_iqr(p, "optimality_gap", ["experiment", "n_attractions"])
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
        ax.axhline(0.0, color="black", linewidth=1)
        ax.set_xlabel("n_attractions")
        ax.set_title(f"{profile} profile")
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("optimality_gap (median, IQR)")
    axes[-1].legend()
    fig.suptitle("Optimality gap vs brute-force (fixture fast_bf suite)")
    save_fig("optimality_gap.png")


if __name__ == "__main__":
    main()
