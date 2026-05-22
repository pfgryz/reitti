from __future__ import annotations

import matplotlib.pyplot as plt

from .common import read_results, save_fig


def main() -> None:
    df = read_results()
    part = df[
        (df["experiment"].isin(["astar_greedy", "astar_intervals"]))
        & (df["status"] == "ok")
        & (df["mode"].isin(["fixture", "real"]))
    ]
    if part.empty:
        return
    for mode in ["fixture", "real"]:
        p = part[part["mode"] == mode]
        if p.empty:
            continue
        x = p.groupby("n_attractions")["wall_time_ms"].mean().reset_index()
        plt.plot(x["n_attractions"], x["wall_time_ms"], marker="o", label=mode)
    plt.xlabel("n_attractions")
    plt.ylabel("wall_time_ms")
    plt.title("Real vs fixture runtime")
    plt.legend()
    save_fig("real_vs_fixture.png")


if __name__ == "__main__":
    main()
