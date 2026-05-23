from __future__ import annotations

import argparse
from typing import Literal

from tqdm import tqdm

from .executor import _run_variants
from .scenarios import (
    make_astar_grid,
    make_boundary_scenarios,
    make_bruteforce_grid,
    make_real_slice,
)
from .suites import build_mode_suites
from .types import (
    ASTAR_GREEDY,
    ASTAR_INTERVALS,
    ASTAR_INTERVALS_NO_H,
    BF_GREEDY,
    BF_INTERVALS,
    DataMode,
    PipelineProfile,
    Row,
)


async def run_grid(args: argparse.Namespace) -> list[Row]:
    rows = await _run_variants(
        scenarios=make_astar_grid(seed_count=args.seed_count),
        variants=[ASTAR_GREEDY, ASTAR_INTERVALS],
        mode=args.matrix_mode,
        timeout_seconds=args.timeout_seconds,
        database_url=args.database_url,
        graphhopper_base_url=args.graphhopper_base_url,
        desc="grid-astar",
    )
    rows.extend(
        await _run_variants(
            scenarios=make_bruteforce_grid(seed_count=args.seed_count),
            variants=[ASTAR_GREEDY, ASTAR_INTERVALS, BF_GREEDY, BF_INTERVALS],
            mode=args.matrix_mode,
            timeout_seconds=args.timeout_seconds,
            database_url=args.database_url,
            graphhopper_base_url=args.graphhopper_base_url,
            desc="grid-bf",
        )
    )
    return rows


async def run_ablation(args: argparse.Namespace) -> list[Row]:
    return await _run_variants(
        scenarios=make_bruteforce_grid(seed_count=args.seed_count),
        variants=[ASTAR_INTERVALS, ASTAR_INTERVALS_NO_H],
        mode=args.matrix_mode,
        timeout_seconds=args.timeout_seconds,
        database_url=args.database_url,
        graphhopper_base_url=args.graphhopper_base_url,
        desc="ablation",
    )


async def run_boundary(args: argparse.Namespace) -> list[Row]:
    rows: list[Row] = []
    boundary = make_boundary_scenarios()
    for scenario in tqdm(
        boundary, total=len(boundary), desc="boundary", unit="scenario", leave=False
    ):
        timeout = (
            0.0001 if scenario.id == "boundary_timeout_bf" else args.timeout_seconds
        )
        rows.extend(
            await _run_variants(
                scenarios=[scenario],
                variants=[
                    ASTAR_GREEDY,
                    ASTAR_INTERVALS,
                    ASTAR_INTERVALS_NO_H,
                    BF_GREEDY,
                    BF_INTERVALS,
                ],
                mode=args.matrix_mode,
                timeout_seconds=timeout,
                database_url=args.database_url,
                graphhopper_base_url=args.graphhopper_base_url,
                desc=f"boundary:{scenario.id}",
            )
        )
    return rows


async def run_real_slice(args: argparse.Namespace) -> list[Row]:
    return await _run_variants(
        scenarios=make_real_slice(),
        variants=[ASTAR_GREEDY, ASTAR_INTERVALS],
        mode="real",
        timeout_seconds=args.timeout_seconds,
        database_url=args.database_url,
        graphhopper_base_url=args.graphhopper_base_url,
        desc="real-slice",
    )


async def _run_suite_for_mode(
    *,
    args: argparse.Namespace,
    mode: Literal["fixture", "real"],
    profile: PipelineProfile,
) -> list[Row]:
    astar_grid, bf_grid, ablation_grid = build_mode_suites(profile=profile, mode=mode)
    rows: list[Row] = []

    rows.extend(
        await _run_variants(
            scenarios=astar_grid,
            variants=[ASTAR_GREEDY, ASTAR_INTERVALS],
            mode=mode,
            timeout_seconds=args.timeout_seconds,
            database_url=args.database_url,
            graphhopper_base_url=args.graphhopper_base_url,
            desc=f"{mode}-grid-astar",
        )
    )
    rows.extend(
        await _run_variants(
            scenarios=bf_grid,
            variants=[ASTAR_GREEDY, ASTAR_INTERVALS, BF_GREEDY, BF_INTERVALS],
            mode=mode,
            timeout_seconds=args.timeout_seconds,
            database_url=args.database_url,
            graphhopper_base_url=args.graphhopper_base_url,
            desc=f"{mode}-grid-bf",
        )
    )
    rows.extend(
        await _run_variants(
            scenarios=ablation_grid,
            variants=[ASTAR_INTERVALS, ASTAR_INTERVALS_NO_H],
            mode=mode,
            timeout_seconds=args.timeout_seconds,
            database_url=args.database_url,
            graphhopper_base_url=args.graphhopper_base_url,
            desc=f"{mode}-ablation",
        )
    )

    boundary = make_boundary_scenarios()
    for scenario in tqdm(
        boundary,
        total=len(boundary),
        desc=f"{mode}-boundary",
        unit="scenario",
        leave=False,
    ):
        timeout = (
            0.0001 if scenario.id == "boundary_timeout_bf" else args.timeout_seconds
        )
        rows.extend(
            await _run_variants(
                scenarios=[scenario],
                variants=[
                    ASTAR_GREEDY,
                    ASTAR_INTERVALS,
                    ASTAR_INTERVALS_NO_H,
                    BF_GREEDY,
                    BF_INTERVALS,
                ],
                mode=mode,
                timeout_seconds=timeout,
                database_url=args.database_url,
                graphhopper_base_url=args.graphhopper_base_url,
                desc=f"{mode}:boundary:{scenario.id}",
            )
        )
    return rows


async def run_pipeline(args: argparse.Namespace) -> list[Row]:
    rows: list[Row] = []
    profile: PipelineProfile = args.profile
    data_mode: DataMode = args.data_mode
    if data_mode in {"fixture", "both"}:
        rows.extend(
            await _run_suite_for_mode(args=args, mode="fixture", profile=profile)
        )
    if data_mode in {"real", "both"}:
        rows.extend(await _run_suite_for_mode(args=args, mode="real", profile=profile))
    return rows


HANDLERS = {
    "run-grid": run_grid,
    "run-ablation": run_ablation,
    "run-boundary": run_boundary,
    "run-real-slice": run_real_slice,
    "run-pipeline": run_pipeline,
}
