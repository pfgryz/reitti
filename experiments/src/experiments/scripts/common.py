from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def outputs_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "outputs"


def figures_dir() -> Path:
    out = outputs_dir() / "figures"
    out.mkdir(parents=True, exist_ok=True)
    return out


def read_results() -> pd.DataFrame:
    return pd.read_csv(outputs_dir() / "results.csv")


def read_aggregated() -> pd.DataFrame:
    return pd.read_csv(outputs_dir() / "aggregated.csv")


def save_fig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(figures_dir() / name, dpi=150)
    plt.close()
