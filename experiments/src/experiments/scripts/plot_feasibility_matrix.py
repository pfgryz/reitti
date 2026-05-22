from __future__ import annotations

import matplotlib.pyplot as plt

from .common import read_results, save_fig


def main() -> None:
    df = read_results()
    if df.empty:
        return
    table = (
        df.groupby(["profile", "status"])
        .size()
        .reset_index(name="count")
        .pivot(index="profile", columns="status", values="count")
        .fillna(0)
    )
    if table.empty:
        return
    plt.imshow(table.values, aspect="auto")
    plt.yticks(range(len(table.index)), table.index)
    plt.xticks(range(len(table.columns)), table.columns, rotation=20, ha="right")
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            plt.text(j, i, int(table.values[i, j]), ha="center", va="center")
    plt.title("Feasibility matrix")
    plt.colorbar()
    save_fig("feasibility_matrix.png")


if __name__ == "__main__":
    main()
