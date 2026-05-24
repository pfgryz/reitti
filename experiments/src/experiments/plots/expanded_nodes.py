from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from .common import (
    annotate_partial_completion,
    fixture_ok_rate,
    profile_label_pl,
    read_results_deduped,
    save_fig,
    summarize_with_iqr,
)


def prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    base = df[
        (df["mode"] == "fixture")
        & (df["status"] == "ok")
        & (df["suite"] != "handpicked_validation")
    ]
    profiles = [p for p in ["relaxed", "tight"] if p in set(base["profile"])]
    if not profiles:
        profiles = sorted(base["profile"].dropna().unique())
    return base, profiles


def render(
    base: pd.DataFrame,
    profiles: list[str],
    rate_table: pd.DataFrame | None = None,
) -> None:
    if base.empty:
        return
    if not profiles:
        return
    fig, axes = plt.subplots(1, len(profiles), figsize=(7 * len(profiles), 5))
    if len(profiles) == 1:
        axes = [axes]
    for ax, profile in zip(axes, profiles):
        part = base[base["profile"] == profile]
        if part.empty:
            continue
        summary = summarize_with_iqr(
            part, "expanded_nodes", ["experiment", "n_attractions"]
        )
        for experiment in sorted(summary["experiment"].unique()):
            s = summary[summary["experiment"] == experiment].sort_values(
                "n_attractions"
            )
            line = ax.errorbar(
                s["n_attractions"],
                s["median"],
                yerr=[s["iqr_low"], s["iqr_high"]],
                marker="o",
                capsize=3,
                label=experiment,
            )
            if rate_table is not None:
                rates = rate_table[
                    (rate_table["profile"] == profile)
                    & (rate_table["experiment"] == experiment)
                ]
                merged = annotate_partial_completion(
                    ax,
                    s,
                    rates,
                    join_columns=["experiment", "n_attractions"],
                )
                partial = merged[merged["ok_rate"] < 1.0]
                if not partial.empty:
                    color = line[0].get_color()
                    ax.scatter(
                        partial["n_attractions"],
                        partial["median"],
                        s=120,
                        facecolors="none",
                        edgecolors=color,
                        linewidths=1.5,
                        zorder=3,
                    )
        ax.set_yscale("log")
        ax.set_xlabel("liczba atrakcji")
        ax.set_title(profile_label_pl(profile))
        ax.grid(alpha=0.2, which="both")
    axes[0].set_ylabel("rozwinięte węzły (mediana, IQR, skala log)")
    axes[-1].legend()
    fig.suptitle(
        "Skalowanie liczby rozwiniętych węzłów (fixture); pusty znacznik = częściowe zakończenie (ok/wszystkie)"
    )
    save_fig("expanded_nodes_scaling.png")


def main() -> None:
    df = read_results_deduped()
    base, profiles = prepare(df)
    rates = fixture_ok_rate(df, ["profile", "experiment", "n_attractions"])
    render(base, profiles, rates)


if __name__ == "__main__":
    main()
