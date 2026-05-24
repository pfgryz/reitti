from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from .common import read_results_deduped, save_fig, summarize_with_iqr


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    return df[
        (df["experiment"].isin(["astar_greedy", "astar_intervals"]))
        & (df["status"] == "ok")
        & (df["mode"].isin(["fixture", "real"]))
    ]


def _render_metric(
    part: pd.DataFrame,
    *,
    metric: str,
    ylabel: str,
    title: str,
    filename: str,
    yscale: str | None = None,
) -> None:
    if part.empty:
        return
    metric_part = part[part[metric].notna()]
    if metric_part.empty:
        return
    experiments = sorted(metric_part["experiment"].unique())
    fig, axes = plt.subplots(
        1, len(experiments), figsize=(7 * len(experiments), 5), sharey=True
    )
    if len(experiments) == 1:
        axes = [axes]
    for ax, experiment in zip(axes, experiments):
        p = metric_part[metric_part["experiment"] == experiment]
        summary = summarize_with_iqr(p, metric, ["mode", "n_attractions"])
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
        if yscale:
            ax.set_yscale(yscale)
        ax.set_xlabel("liczba atrakcji")
        ax.set_title(experiment)
        ax.grid(alpha=0.2, which="both")
    axes[0].set_ylabel(ylabel)
    axes[-1].legend()
    fig.suptitle(title)
    save_fig(filename)


def render(part: pd.DataFrame) -> None:
    _render_metric(
        part,
        metric="wall_time_ms",
        ylabel="czas wykonania [ms] (mediana, IQR)",
        title="Środowisko rzeczywiste vs fixture: czas wykonania",
        filename="real_vs_fixture.png",
    )
    _render_metric(
        part,
        metric="peak_memory_mb",
        ylabel="szczyt zużycia pamięci [MB] (mediana, IQR, skala log)",
        title="Środowisko rzeczywiste vs fixture: pamięć",
        filename="real_vs_fixture_memory.png",
        yscale="log",
    )


def main() -> None:
    render(prepare(read_results_deduped()))


if __name__ == "__main__":
    main()
