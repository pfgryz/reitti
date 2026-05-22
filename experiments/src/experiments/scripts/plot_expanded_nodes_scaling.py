from __future__ import annotations

import matplotlib.pyplot as plt

from .common import read_aggregated, save_fig


def main() -> None:
    df = read_aggregated()
    if df.empty:
        return
    for experiment in sorted(df["experiment"].unique()):
        part = df[(df["experiment"] == experiment) & (df["mode"] == "fixture")]
        if part.empty:
            continue
        plt.plot(
            part["n_attractions"],
            part["expanded_nodes_mean"],
            marker="o",
            label=experiment,
        )
    plt.xlabel("n_attractions")
    plt.ylabel("expanded_nodes_mean")
    plt.title("Expanded nodes scaling (fixture)")
    plt.legend()
    save_fig("expanded_nodes_scaling.png")


if __name__ == "__main__":
    main()
