from __future__ import annotations

import pandas as pd


def expected_status(experiment: str, scenario_id: str, profile: str) -> str | None:
    if scenario_id in {"boundary_all_impossible", "boundary_single_unreachable"}:
        return "infeasible"
    if scenario_id == "boundary_empty_only_start":
        return "ok"
    if scenario_id == "boundary_timeout_bf" and experiment.startswith("bruteforce"):
        return "timeout"
    if profile == "impossible":
        return "infeasible"
    return None


def add_feasibility_correctness(df: pd.DataFrame) -> pd.DataFrame:
    """Mark whether observed status matches scenario-specific feasibility rules.

    Adds/updates ``feasibility_correctness`` as a boolean flag:
    ``str(status) == expected_status(experiment, scenario_id, profile)`` for rows
    where an expected status is defined; other rows remain missing.
    """
    out = df.copy()
    if "feasibility_correctness" not in out.columns:
        out["feasibility_correctness"] = pd.NA
    for idx, row in out.iterrows():
        expected = expected_status(
            str(row["experiment"]),
            str(row["scenario_id"]),
            str(row["profile"]),
        )
        if expected is not None:
            out.at[idx, "feasibility_correctness"] = str(row["status"]) == expected
    return out
