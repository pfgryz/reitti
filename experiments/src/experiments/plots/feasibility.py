from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from .common import read_results_deduped, save_fig


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    return df[
        (df["suite"] == "handpicked_validation")
        & (df["experiment"] == "astar_intervals")
    ]


def render(part: pd.DataFrame) -> None:
    if part.empty:
        return
    modes = [m for m in ["fixture", "real"] if m in set(part["mode"])]
    if not modes:
        return
    fig, axes = plt.subplots(1, len(modes), figsize=(6 * len(modes), 5), sharey=True)
    if len(modes) == 1:
        axes = [axes]
    for ax, mode in zip(axes, modes):
        mode_part = part[part["mode"] == mode]
        table = (
            mode_part.groupby(["profile", "status"])
            .size()
            .reset_index(name="count")
            .pivot(index="profile", columns="status", values="count")
            .fillna(0)
        )
        if table.empty:
            continue
        im = ax.imshow(table.values, aspect="auto")
        ax.set_yticks(range(len(table.index)), table.index)
        ax.set_xticks(range(len(table.columns)), table.columns, rotation=20, ha="right")
        for i in range(table.shape[0]):
            for j in range(table.shape[1]):
                ax.text(j, i, int(table.values[i, j]), ha="center", va="center")
        ax.set_title(f"{mode} mode")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle("Feasibility matrix (boundary scenarios)")
    save_fig("feasibility_matrix.png")


def main() -> None:
    render(prepare(read_results_deduped()))


if __name__ == "__main__":
    main()
