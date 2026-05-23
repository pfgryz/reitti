from __future__ import annotations

from experiments.plots.common import outputs_dir


def read_aggregated():
    import pandas as pd

    path = outputs_dir() / "aggregated.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def main() -> None:
    df = read_aggregated()
    report = outputs_dir().parents[0] / "reports" / "summary.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        report.write_text(
            "# Experiment Summary\n\nNo aggregated results.\n", encoding="utf-8"
        )
        return
    top = df.sort_values(["experiment", "n_attractions"]).head(40)
    csv_preview = top.to_csv(index=False)
    report.write_text(
        "# Experiment Summary\n\n"
        "Generated from `outputs/aggregated.csv`.\n\n"
        "```csv\n" + csv_preview + "```\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
