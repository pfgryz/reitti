from __future__ import annotations

import matplotlib.pyplot as plt

from .common import read_results, save_fig


def main() -> None:
    df = read_results()
    part = df[
        (df["mode"] == "fixture")
        & (df["experiment"].isin(["astar_intervals", "astar_intervals_no_heuristic"]))
        & (df["status"] == "ok")
    ]
    if part.empty:
        return
    for exp in sorted(part["experiment"].unique()):
        p = part[part["experiment"] == exp]
        x = p.groupby("n_attractions")["wall_time_ms"].mean().reset_index()
        plt.plot(x["n_attractions"], x["wall_time_ms"], marker="o", label=exp)
    plt.ylabel("wall_time_ms")
    plt.xlabel("n_attractions")
    plt.title("Heuristic ablation runtime")
    plt.legend()
    save_fig("heuristic_ablation.png")


if __name__ == "__main__":
    main()
