from __future__ import annotations

import pandas as pd

from .feasibility import add_feasibility_correctness
from .gap import add_optimality_gap
from .speedup import add_heuristic_speedup


def enrich_results(df: pd.DataFrame) -> pd.DataFrame:
    out = add_optimality_gap(df)
    out = add_heuristic_speedup(out)
    out = add_feasibility_correctness(out)
    return out
