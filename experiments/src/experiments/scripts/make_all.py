from __future__ import annotations

from . import (
    build_docs_report,
    build_summary_table,
    plot_expanded_nodes_scaling,
    plot_feasibility_matrix,
    plot_heuristic_ablation,
    plot_memory_scaling,
    plot_optimality_gap,
    plot_quality_boxplot,
    plot_real_vs_fixture,
    plot_runtime_scaling,
)


def main() -> None:
    plot_runtime_scaling.main()
    plot_expanded_nodes_scaling.main()
    plot_memory_scaling.main()
    plot_quality_boxplot.main()
    plot_optimality_gap.main()
    plot_heuristic_ablation.main()
    plot_feasibility_matrix.main()
    plot_real_vs_fixture.main()
    build_summary_table.main()
    build_docs_report.main()


if __name__ == "__main__":
    main()
