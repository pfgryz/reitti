from __future__ import annotations

import pandas as pd


def add_optimality_gap(df: pd.DataFrame) -> pd.DataFrame:
    """Populate A* rows with baseline objective and relative optimality gap.

    Adds/updates two derived columns:
    - ``bf_objective``: matched brute-force ``objective_cost`` for the same
      ``scenario_id``, ``mode``, and ``stay_mode``.
    - ``optimality_gap``: ``(objective_cost - bf_objective) / bf_objective``
      for successful A* experiments.
    """
    out = df.copy()
    if "bf_objective" not in out.columns:
        out["bf_objective"] = pd.NA
    if "optimality_gap" not in out.columns:
        out["optimality_gap"] = pd.NA

    bf = out[
        out["experiment"].isin(["bruteforce_greedy", "bruteforce_intervals"])
        & (out["status"] == "ok")
    ][["scenario_id", "mode", "stay_mode", "objective_cost"]].rename(
        columns={"objective_cost": "bf_obj"}
    )
    astar_mask = out["experiment"].isin(
        ["astar_greedy", "astar_intervals", "astar_intervals_no_heuristic"]
    ) & (out["status"] == "ok")
    merged = out[astar_mask].merge(
        bf, on=["scenario_id", "mode", "stay_mode"], how="left"
    )
    out.loc[astar_mask, "bf_objective"] = merged["bf_obj"].values
    out.loc[astar_mask, "optimality_gap"] = (
        (merged["objective_cost"] - merged["bf_obj"]) / merged["bf_obj"]
    ).values
    return out
