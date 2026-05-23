from __future__ import annotations

import matplotlib.pyplot as plt

from .common import read_results_deduped, save_fig


def main() -> None:
    df = read_results_deduped()
    if df.empty:
        return
    # Use one canonical solver to avoid multiplying counts by algorithm count.
    canonical = df[df["experiment"] == "astar_intervals"]
    if canonical.empty:
        return
    modes = [m for m in ["fixture", "real"] if m in set(canonical["mode"])]
    fig, axes = plt.subplots(1, len(modes), figsize=(6 * len(modes), 5), sharey=True)
    if len(modes) == 1:
        axes = [axes]

    for ax, mode in zip(axes, modes):
        part = canonical[canonical["mode"] == mode]
        table = (
            part.groupby(["profile", "status"])
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
    fig.suptitle("Feasibility matrix (canonical astar_intervals rows)")
    save_fig("feasibility_matrix.png")


if __name__ == "__main__":
    main()
