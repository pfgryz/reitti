from __future__ import annotations

import time
import tracemalloc

from tqdm import tqdm

from .matrices import MatrixProvider
from .metrics import quality, walk_total
from .rows import row_error, row_ok, status_from_error
from .scenarios import Scenario
from .solver import run_variant
from .types import Row, Variant

BRUTEFORCE_MAX_ATTRACTIONS = 10


def _append_suite_timeout_skips(
    *,
    rows: list[Row],
    scenarios: list[Scenario],
    variants: list[Variant],
    mode: str,
    start_scenario_idx: int,
    start_variant_idx: int,
    suite_timeout_seconds: float,
    bar,
) -> None:
    msg = f"suite timed out after {suite_timeout_seconds:.1f}s"
    for s_idx in range(start_scenario_idx, len(scenarios)):
        scenario = scenarios[s_idx]
        v_start = start_variant_idx if s_idx == start_scenario_idx else 0
        for v_idx in range(v_start, len(variants)):
            rows.append(
                row_error(
                    variant=variants[v_idx],
                    scenario=scenario,
                    mode=mode,
                    status="skipped",
                    error=msg,
                )
            )
            bar.update(1)


async def run_case(
    *,
    variant: Variant,
    scenario: Scenario,
    mode: str,
    timeout_seconds: float,
    astar_timeout_seconds: float | None = None,
    matrices,
) -> Row:
    if (
        variant.algorithm == "bruteforce"
        and scenario.n_attractions > BRUTEFORCE_MAX_ATTRACTIONS
    ):
        return row_error(
            variant=variant,
            scenario=scenario,
            mode=mode,
            status="skipped",
            error=f"n_attractions>{BRUTEFORCE_MAX_ATTRACTIONS}",
        )

    try:
        tracemalloc.start()
        peak_bytes: int | None = None
        try:
            result, stats, wall = await run_variant(
                variant=variant,
                scenario=scenario,
                matrices=matrices,
                timeout_seconds=timeout_seconds,
                astar_timeout_seconds=astar_timeout_seconds,
            )
            _, peak_bytes = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        walk = await walk_total(result.visits, matrices)
        total_stay, utilization, objective = quality(
            scenario.problem,
            result.visits,
            walk,
        )
        return row_ok(
            variant=variant,
            scenario=scenario,
            mode=mode,
            wall_time_ms=wall,
            peak_memory_mb=(peak_bytes / (1024 * 1024))
            if peak_bytes is not None
            else None,
            expanded_nodes=stats.expanded_nodes,
            generated_nodes=stats.generated_nodes,
            pruned_by_best_g=stats.pruned_by_best_g,
            visits_count=len(result.visits),
            total_stay_minutes=total_stay,
            stay_utilization=utilization,
            total_walk_distance_m=walk,
            objective_cost=objective,
            end_time=result.end_time,
        )
    except Exception as exc:
        status = status_from_error(exc)
        print(
            f"[CASE-{status.upper()}] scenario={scenario.id} variant={variant.name} error={exc}"
        )
        return row_error(
            variant=variant,
            scenario=scenario,
            mode=mode,
            status=status,
            error=str(exc),
        )


async def run_suite(
    *,
    scenarios: list[Scenario],
    variants: list[Variant],
    mode: str,
    timeout_seconds: float,
    astar_timeout_seconds: float | None = None,
    suite_timeout_seconds: float | None = None,
    matrix_provider: MatrixProvider,
    desc: str,
) -> list[Row]:
    rows: list[Row] = []
    total = len(scenarios) * len(variants)
    bar = tqdm(total=total, desc=desc, unit="run", leave=False)
    started = time.monotonic()
    for s_idx, scenario in enumerate(scenarios):
        bar.set_description(f"{desc}:n={scenario.n_attractions}")
        if (
            suite_timeout_seconds is not None
            and time.monotonic() - started >= suite_timeout_seconds
        ):
            _append_suite_timeout_skips(
                rows=rows,
                scenarios=scenarios,
                variants=variants,
                mode=mode,
                start_scenario_idx=s_idx,
                start_variant_idx=0,
                suite_timeout_seconds=suite_timeout_seconds,
                bar=bar,
            )
            break
        try:
            async with matrix_provider.acquire(scenario) as matrices:
                for v_idx, variant in enumerate(variants):
                    if (
                        suite_timeout_seconds is not None
                        and time.monotonic() - started >= suite_timeout_seconds
                    ):
                        _append_suite_timeout_skips(
                            rows=rows,
                            scenarios=scenarios,
                            variants=variants,
                            mode=mode,
                            start_scenario_idx=s_idx,
                            start_variant_idx=v_idx,
                            suite_timeout_seconds=suite_timeout_seconds,
                            bar=bar,
                        )
                        bar.close()
                        return rows
                    rows.append(
                        await run_case(
                            variant=variant,
                            scenario=scenario,
                            mode=mode,
                            timeout_seconds=timeout_seconds,
                            astar_timeout_seconds=astar_timeout_seconds,
                            matrices=matrices,
                        )
                    )
                    bar.update(1)
        except Exception as exc:
            status = status_from_error(exc)
            for variant in variants:
                rows.append(
                    row_error(
                        variant=variant,
                        scenario=scenario,
                        mode=mode,
                        status=status,
                        error=str(exc),
                    )
                )
                bar.update(1)
    bar.close()
    return rows
