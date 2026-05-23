from __future__ import annotations

import pandas as pd


def add_heuristic_speedup(df: pd.DataFrame) -> pd.DataFrame:
    """Populate heuristic speedup for paired interval A* experiment rows.

    Adds/updates ``heuristic_speedup`` for matching ``scenario_id`` and ``mode``
    pairs from successful runs as ``t_no_h / t_h``, where ``t_h`` is
    ``wall_time_ms`` from ``astar_intervals`` and ``t_no_h`` is ``wall_time_ms``
    from ``astar_intervals_no_heuristic``.
    """
    out = df.copy()
    if "heuristic_speedup" not in out.columns:
        out["heuristic_speedup"] = pd.NA

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
    return out
