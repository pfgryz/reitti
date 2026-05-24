from __future__ import annotations

from ..scripts import build_docs_report, build_summary_table
from . import (
    ablation,
    expanded_nodes,
    memory,
    real_vs_fixture,
    runtime,
)


def main() -> None:
    runtime.main()
    memory.main()
    real_vs_fixture.main()
    expanded_nodes.main()
    ablation.main()
    build_summary_table.main()
    build_docs_report.main()


if __name__ == "__main__":
    main()
