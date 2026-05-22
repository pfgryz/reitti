from __future__ import annotations

import matplotlib.pyplot as plt

from .common import read_results, save_fig


def main() -> None:
    df = read_results()
    part = df[
        (df["mode"] == "fixture")
        & (df["experiment"].str.startswith("astar"))
        & (df["optimality_gap"].notna())
    ]
    if part.empty:
        return
    for exp in sorted(part["experiment"].unique()):
        p = part[part["experiment"] == exp]
        x = p.groupby("n_attractions")["optimality_gap"].mean().reset_index()
        plt.plot(x["n_attractions"], x["optimality_gap"], marker="o", label=exp)
    plt.axhline(0.0, color="black", linewidth=1)
    plt.ylabel("optimality_gap")
    plt.xlabel("n_attractions")
    plt.title("Optimality gap vs brute-force")
    plt.legend()
    save_fig("optimality_gap.png")


if __name__ == "__main__":
    main()
