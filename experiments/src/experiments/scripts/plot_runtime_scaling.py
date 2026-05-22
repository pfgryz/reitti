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
            part["wall_time_ms_mean"],
            marker="o",
            label=experiment,
        )
    plt.yscale("log")
    plt.xlabel("n_attractions")
    plt.ylabel("wall_time_ms_mean")
    plt.title("Runtime scaling (fixture)")
    plt.legend()
    save_fig("runtime_scaling.png")


if __name__ == "__main__":
    main()
