from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from .common import outputs_dir, read_aggregated, read_results

FIGURE_ORDER = [
    "runtime_scaling.png",
    "expanded_nodes_scaling.png",
    "memory_scaling.png",
    "quality_boxplot.png",
    "optimality_gap.png",
    "heuristic_ablation.png",
    "feasibility_matrix.png",
    "real_vs_fixture.png",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _docs_root() -> Path:
    return _repo_root() / "docs"


def _docs_figure_dir() -> Path:
    out = _docs_root() / "figures" / "experiments"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No data._"
    cols = list(df.columns)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = [
        "| " + " | ".join(str(v) for v in row) + " |"
        for row in df.itertuples(index=False, name=None)
    ]
    return "\n".join([header, sep, *rows])


def _copy_figures() -> list[str]:
    src_dir = outputs_dir() / "figures"
    dst_dir = _docs_figure_dir()
    copied: list[str] = []
    for name in FIGURE_ORDER:
        src = src_dir / name
        if not src.exists():
            continue
        dst = dst_dir / name
        shutil.copy2(src, dst)
        copied.append(name)
    return copied


def _status_summary(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame(columns=["mode", "experiment", "runs", "ok", "ok_rate"])
    table = (
        results.groupby(["mode", "experiment"], dropna=False)
        .agg(
            runs=("experiment", "count"),
            ok=("status", lambda s: int((s == "ok").sum())),
        )
        .reset_index()
    )
    table["ok_rate"] = (table["ok"] / table["runs"]).round(3)
    return table.sort_values(["mode", "experiment"])


def _runtime_quality_summary(agg: pd.DataFrame) -> pd.DataFrame:
    if agg.empty:
        return pd.DataFrame(
            columns=[
                "mode",
                "experiment",
                "avg_ok_rate",
                "avg_wall_time_ms",
                "avg_expanded_nodes",
                "avg_peak_memory_mb",
                "median_objective_cost",
                "avg_stay_utilization",
            ]
        )
    part = agg.copy()
    part["ok_rate"] = part["ok_count"] / part["run_count"].where(
        part["run_count"] > 0, 1
    )
    out = (
        part.groupby(["mode", "experiment"], dropna=False)
        .agg(
            avg_ok_rate=("ok_rate", "mean"),
            avg_wall_time_ms=("wall_time_ms_mean", "mean"),
            avg_expanded_nodes=("expanded_nodes_mean", "mean"),
            avg_peak_memory_mb=("peak_memory_mb_mean", "mean"),
            median_objective_cost=("objective_cost_median", "median"),
            avg_stay_utilization=("stay_utilization_mean", "mean"),
        )
        .reset_index()
    )
    numeric_cols = [c for c in out.columns if c not in {"mode", "experiment"}]
    out[numeric_cols] = out[numeric_cols].round(3)
    return out.sort_values(["mode", "experiment"])


def _heuristic_summary(results: pd.DataFrame) -> pd.DataFrame:
    part = results[results["heuristic_speedup"].notna()].copy()
    if part.empty:
        return pd.DataFrame(
            columns=["mode", "mean_speedup_vs_no_heuristic", "sample_count"]
        )
    out = (
        part.groupby("mode", dropna=False)
        .agg(
            mean_speedup_vs_no_heuristic=("heuristic_speedup", "mean"),
            sample_count=("heuristic_speedup", "count"),
        )
        .reset_index()
    )
    out["mean_speedup_vs_no_heuristic"] = out["mean_speedup_vs_no_heuristic"].round(3)
    return out


def _feasibility_summary(results: pd.DataFrame) -> pd.DataFrame:
    part = results[results["feasibility_correctness"].notna()].copy()
    if part.empty:
        return pd.DataFrame(
            columns=["mode", "checked_cases", "correct_cases", "correct_rate"]
        )
    part["is_correct"] = part["feasibility_correctness"].astype(bool)
    out = (
        part.groupby("mode", dropna=False)
        .agg(
            checked_cases=("is_correct", "count"),
            correct_cases=("is_correct", "sum"),
        )
        .reset_index()
    )
    out["correct_rate"] = (out["correct_cases"] / out["checked_cases"]).round(3)
    return out


def _render_markdown(
    *,
    copied_figures: list[str],
    status: pd.DataFrame,
    runtime_quality: pd.DataFrame,
    heuristic: pd.DataFrame,
    feasibility: pd.DataFrame,
) -> str:
    fig_lines = []
    for name in copied_figures:
        title = name.replace(".png", "").replace("_", " ")
        fig_lines.append(
            f"### {title.title()}\n\n![{title}](figures/experiments/{name})\n"
        )
    if not fig_lines:
        fig_lines.append("_No figures found in `experiments/outputs/figures`._")

    return (
        "# Experiments Report\n\n"
        "Generated automatically from `experiments/outputs/results.csv` and "
        "`experiments/outputs/aggregated.csv`.\n\n"
        "## Setup\n\n"
        "### Prerequisites\n"
        "- Python env synced in `experiments/` (`just sync`).\n"
        "- For real-mode runs: GraphHopper + PostGIS started and loaded.\n\n"
        "### Run commands\n"
        "- Fast synthetic: `just experiments-fast-fixture`\n"
        "- Fast real: `just experiments-fast-real`\n"
        "- Fast both: `just experiments-fast-both`\n"
        "- Full synthetic: `just experiments-full-fixture`\n"
        "- Full real: `just experiments-full-real`\n"
        "- Full both: `just experiments-full-both`\n\n"
        "## Experiment Justification\n\n"
        "- **A* greedy vs A* intervals**: checks quality/runtime trade-off "
        "from richer stay-time branching.\n"
        "- **Ablation (heuristic off)**: isolates value of heuristic guidance "
        "in search speed.\n"
        "- **Brute-force baseline**: provides reference objective for "
        "small/feasible cases.\n"
        "- **Boundary cases**: verifies infeasible/timeout handling and robustness.\n"
        "- **Synthetic vs real matrices**: tests if trends hold when using "
        "true Helsinki routing stack.\n\n"
        "## Key Tables\n\n"
        "### Status by mode and experiment\n\n"
        f"{_markdown_table(status)}\n\n"
        "### Runtime and quality summary\n\n"
        f"{_markdown_table(runtime_quality)}\n\n"
        "### Heuristic speedup summary\n\n"
        f"{_markdown_table(heuristic)}\n\n"
        "### Feasibility correctness summary\n\n"
        f"{_markdown_table(feasibility)}\n\n"
        "## Final Plots\n\n" + "\n".join(fig_lines) + "\n"
    )


def main() -> None:
    docs_report = _docs_root() / "experiments.md"
    results = (
        read_results() if (outputs_dir() / "results.csv").exists() else pd.DataFrame()
    )
    agg = (
        read_aggregated()
        if (outputs_dir() / "aggregated.csv").exists()
        else pd.DataFrame()
    )
    copied = _copy_figures()
    content = _render_markdown(
        copied_figures=copied,
        status=_status_summary(results),
        runtime_quality=_runtime_quality_summary(agg),
        heuristic=_heuristic_summary(results),
        feasibility=_feasibility_summary(results),
    )
    docs_report.write_text(content, encoding="utf-8")
    print(f"wrote docs report: {docs_report}")


if __name__ == "__main__":
    main()
