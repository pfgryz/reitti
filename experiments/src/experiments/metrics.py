from __future__ import annotations

import pandas as pd

from . import ensure_backend_path

ensure_backend_path()

from core.route_optimizer import ALPHA, BETA, RouteOptimizationInput  # noqa: E402


async def _walk_total(visits: tuple, matrices) -> float:
    total = 0.0
    current = 0
    for visit in visits:
        nxt = visit.attraction_index
        total += await matrices.walk_dist.get(current, nxt)
        current = nxt
    return total


def _quality(
    problem: RouteOptimizationInput, visits: tuple, walk_distance_m: float
) -> tuple[float, float, float]:
    total_stay = sum(v.departure_time - v.arrival_time for v in visits)
    used = {v.attraction_index: v.departure_time - v.arrival_time for v in visits}
    total_max = sum(a.stay.max for a in problem.attractions[1:])
    unused = problem.attractions[0].stay.max
    for idx, attraction in enumerate(problem.attractions):
        if idx == 0:
            continue
        unused += attraction.stay.max - used.get(idx, 0.0)
    stay_utilization = (total_stay / total_max) if total_max > 0 else 1.0
    objective = ALPHA * walk_distance_m + BETA * unused
    return total_stay, stay_utilization, objective


def _expected_status(experiment: str, scenario_id: str, profile: str) -> str | None:
    if scenario_id in {"boundary_all_impossible", "boundary_single_unreachable"}:
        return "infeasible"
    if scenario_id == "boundary_empty_only_start":
        return "ok"
    if scenario_id == "boundary_timeout_bf" and experiment.startswith("bruteforce"):
        return "timeout"
    if profile == "impossible":
        return "infeasible"
    return None


def _enrich_results(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["bf_objective"] = pd.NA
    out["optimality_gap"] = pd.NA
    out["heuristic_speedup"] = pd.NA
    out["feasibility_correctness"] = pd.NA

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

    h = out[(out["experiment"] == "astar_intervals") & (out["status"] == "ok")][
        ["scenario_id", "mode", "wall_time_ms"]
    ].rename(columns={"wall_time_ms": "t_h"})
    nh = out[
        (out["experiment"] == "astar_intervals_no_heuristic") & (out["status"] == "ok")
    ][["scenario_id", "mode", "wall_time_ms"]].rename(
        columns={"wall_time_ms": "t_no_h"}
    )
    hs = h.merge(nh, on=["scenario_id", "mode"], how="inner")
    hs["speedup"] = hs["t_no_h"] / hs["t_h"]
    speed = {(r["scenario_id"], r["mode"]): r["speedup"] for _, r in hs.iterrows()}
    for idx, row in out.iterrows():
        key = (row["scenario_id"], row["mode"])
        if key in speed and row["experiment"] in {
            "astar_intervals",
            "astar_intervals_no_heuristic",
        }:
            out.at[idx, "heuristic_speedup"] = speed[key]

    for idx, row in out.iterrows():
        expected = _expected_status(
            row["experiment"], row["scenario_id"], row["profile"]
        )
        if expected is not None:
            out.at[idx, "feasibility_correctness"] = row["status"] == expected
    return out
