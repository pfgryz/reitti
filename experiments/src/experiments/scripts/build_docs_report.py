from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from experiments.plots.common import outputs_dir, read_results


def read_aggregated() -> pd.DataFrame:
    path = outputs_dir() / "aggregated.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


PRIMARY_FIGURES = [
    ("runtime_scaling.png", "Runtime scaling (fixture)"),
    ("memory_scaling.png", "Memory scaling (fixture)"),
    ("real_vs_fixture.png", "Real vs fixture runtime"),
    ("real_vs_fixture_memory.png", "Real vs fixture memory"),
]

APPENDIX_FIGURES = [
    ("expanded_nodes_scaling.png", "Expanded nodes scaling (fixture)"),
    ("heuristic_ablation.png", "Heuristic ablation runtime (fixture)"),
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


def _copy_figures() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    src_dir = outputs_dir() / "figures"
    dst_dir = _docs_figure_dir()

    def _copy(group: list[tuple[str, str]]) -> list[tuple[str, str]]:
        present: list[tuple[str, str]] = []
        for name, title in group:
            src = src_dir / name
            if not src.exists():
                continue
            shutil.copy2(src, dst_dir / name)
            present.append((name, title))
        return present

    return _copy(PRIMARY_FIGURES), _copy(APPENDIX_FIGURES)


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
    if "heuristic_speedup" not in results.columns:
        return pd.DataFrame(
            columns=["mode", "mean_speedup_vs_no_heuristic", "sample_count"]
        )
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
    if "feasibility_correctness" not in results.columns:
        return pd.DataFrame(
            columns=["mode", "checked_cases", "correct_cases", "correct_rate"]
        )
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


def _gap_summary(results: pd.DataFrame) -> pd.DataFrame:
    """Per-algorithm summary of the optimality gap vs brute-force.

    Replaces `optimality_gap.png` and `quality_boxplot.png`: a tiny table
    is more informative than plotting a quantity that is essentially zero
    everywhere on every solvable instance.
    """
    if "optimality_gap" not in results.columns:
        return pd.DataFrame(
            columns=[
                "experiment",
                "profile",
                "compared_cases",
                "max_abs_gap",
                "median_abs_gap",
            ]
        )
    part = results[results["optimality_gap"].notna()].copy()
    if part.empty:
        return pd.DataFrame(
            columns=[
                "experiment",
                "profile",
                "compared_cases",
                "max_abs_gap",
                "median_abs_gap",
            ]
        )
    part["abs_gap"] = part["optimality_gap"].abs()
    out = (
        part.groupby(["experiment", "profile"], dropna=False)
        .agg(
            compared_cases=("abs_gap", "count"),
            max_abs_gap=("abs_gap", "max"),
            median_abs_gap=("abs_gap", "median"),
        )
        .reset_index()
    )
    out["max_abs_gap"] = out["max_abs_gap"].map(lambda v: f"{v:.2e}")
    out["median_abs_gap"] = out["median_abs_gap"].map(lambda v: f"{v:.2e}")
    return out.sort_values(["experiment", "profile"])


def _figure_section(figures: list[tuple[str, str]]) -> str:
    if not figures:
        return "_No figures found in `experiments/outputs/figures`._\n"
    lines: list[str] = []
    for name, title in figures:
        lines.append(f"### {title}\n\n![{title}](figures/experiments/{name})\n")
    return "\n".join(lines) + "\n"


def _render_markdown(
    *,
    primary_figures: list[tuple[str, str]],
    appendix_figures: list[tuple[str, str]],
    status: pd.DataFrame,
    runtime_quality: pd.DataFrame,
    heuristic: pd.DataFrame,
    feasibility: pd.DataFrame,
    gap: pd.DataFrame,
) -> str:
    return (
        "# Experiments Report\n\n"
        "Generated automatically from `experiments/outputs/results.csv` and "
        "`experiments/outputs/aggregated.csv`.\n\n"
        "## Setup\n\n"
        "### Prerequisites\n"
        "- Python env synced in `experiments/` (`just sync`).\n"
        "- For real-mode runs: GraphHopper + PostGIS started and loaded.\n\n"
        "### Run commands\n"
        "- Synthetic main: `uv run python -m experiments.app suite=synthetic_main setup=baseline`\n"
        "- Heuristic ablation: `uv run python -m experiments.app suite=heuristic_ablation setup=baseline`\n"
        "- BF reference: `uv run python -m experiments.app suite=bf_reference_small_n setup=window_stress`\n"
        "- Handpicked validation: `uv run python -m experiments.app suite=handpicked_validation setup=infeasible_sanity`\n"
        "- Real reference: `uv run python -m experiments.app suite=real_reference setup=real_reference matrix.mode=real infra.database_url=... infra.graphhopper_base_url=...`\n\n"
        "## Reading the figures\n\n"
        "- Each scaling figure has a **relaxed** and **tight** profile panel "
        "(time-window pressure). Tight windows prune the search aggressively, "
        "so absolute numbers stay much smaller than under relaxed windows.\n"
        "- Y-axes are **logarithmic** on scaling plots. A drop or plateau "
        "near the right edge of a curve usually means the algorithm hit the "
        "timeout on the harder scenarios (see `ok/total` annotation).\n"
        "- A **hollow marker** with `k/n` next to it means only `k` out of "
        "`n` runs at that `n_attractions` finished within the timeout. The "
        "plotted median therefore reflects only the easier survivors and "
        "should be read as a lower bound.\n"
        "- Concretely: `bruteforce_intervals` peaks around `n=9` relaxed and "
        "appears to *drop* at `n=10` purely because 11 of 12 scenarios "
        "timed out at `n=10` and only the cheapest one survived.\n\n"
        "## Practical takeaways\n\n"
        "- A* with the interval branching matches greedy A* on quality and "
        "stays well under one second up to `n_attractions = 12` on synthetic "
        "fixtures (see runtime scaling). At `n=15` the relaxed profile "
        "becomes the harder regime and only the tight profile finishes.\n"
        "- Brute-force baselines confirm A* is optimal on every solvable "
        "case (see optimality-gap table below: max gap is essentially "
        "floating-point noise).\n"
        "- Real Helsinki-stack runs are dominated by GraphHopper / PostGIS "
        "round-trips: walltime is roughly two orders of magnitude above the "
        "synthetic fixture for the same `n_attractions`, while the search "
        "itself expands the same number of nodes (see real-vs-fixture).\n\n"
        "## Key tables\n\n"
        "### Status by mode and experiment\n\n"
        f"{_markdown_table(status)}\n\n"
        "### Runtime and quality summary\n\n"
        f"{_markdown_table(runtime_quality)}\n\n"
        "### Optimality gap vs brute-force (per algorithm / profile)\n\n"
        f"{_markdown_table(gap)}\n\n"
        "### Heuristic speedup summary\n\n"
        f"{_markdown_table(heuristic)}\n\n"
        "### Feasibility correctness summary (handpicked boundary suite)\n\n"
        f"{_markdown_table(feasibility)}\n\n"
        "## Final plots\n\n"
        f"{_figure_section(primary_figures)}\n"
        "## Appendix: internal search metrics\n\n"
        "These figures describe algorithm internals (search effort, "
        "heuristic ablation) rather than user-facing performance. They are "
        "kept for completeness.\n\n"
        f"{_figure_section(appendix_figures)}"
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
    primary, appendix = _copy_figures()
    content = _render_markdown(
        primary_figures=primary,
        appendix_figures=appendix,
        status=_status_summary(results),
        runtime_quality=_runtime_quality_summary(agg),
        heuristic=_heuristic_summary(results),
        feasibility=_feasibility_summary(results),
        gap=_gap_summary(results),
    )
    docs_report.write_text(content, encoding="utf-8")
    print(f"wrote docs report: {docs_report}")


if __name__ == "__main__":
    main()
