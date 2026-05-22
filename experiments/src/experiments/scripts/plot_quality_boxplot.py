from __future__ import annotations

import matplotlib.pyplot as plt

from .common import read_results, save_fig


def main() -> None:
    df = read_results()
    part = df[(df["mode"] == "fixture") & (df["status"] == "ok")]
    if part.empty:
        return
    exps = sorted(part["experiment"].unique())
    data = [
        part[part["experiment"] == e]["objective_cost"].dropna().values for e in exps
    ]
    plt.boxplot(data, tick_labels=exps)
    plt.xticks(rotation=20, ha="right")
    plt.ylabel("objective_cost")
    plt.title("Quality distribution by algorithm")
    save_fig("quality_boxplot.png")


if __name__ == "__main__":
    main()
