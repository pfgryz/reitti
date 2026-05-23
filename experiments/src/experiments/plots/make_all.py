from __future__ import annotations

from ..scripts import build_docs_report, build_summary_table
from . import (
    ablation,
    expanded_nodes,
    feasibility,
    gap,
    memory,
    quality,
    real_vs_fixture,
    runtime,
)


def main() -> None:
    runtime.main()
    expanded_nodes.main()
    memory.main()
    quality.main()
    gap.main()
    ablation.main()
    feasibility.main()
    real_vs_fixture.main()
    build_summary_table.main()
    build_docs_report.main()


if __name__ == "__main__":
    main()
