from __future__ import annotations

import tracemalloc

from tqdm import tqdm

from .matrices import MatrixProvider
from .metrics import quality, walk_total
from .rows import row_error, row_ok, status_from_error
from .scenarios import Scenario
from .solver import run_variant
from .types import Row, Variant

BRUTEFORCE_MAX_ATTRACTIONS = 10


async def run_case(
    *,
    variant: Variant,
    scenario: Scenario,
    mode: str,
    timeout_seconds: float,
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
        return row_error(
            variant=variant,
            scenario=scenario,
            mode=mode,
            status=status_from_error(exc),
            error=str(exc),
        )


async def run_suite(
    *,
    scenarios: list[Scenario],
    variants: list[Variant],
    mode: str,
    timeout_seconds: float,
    matrix_provider: MatrixProvider,
    desc: str,
) -> list[Row]:
    rows: list[Row] = []
    total = len(scenarios) * len(variants)
    bar = tqdm(total=total, desc=desc, unit="run", leave=False)
    for scenario in scenarios:
        try:
            async with matrix_provider.acquire(scenario) as matrices:
                for variant in variants:
                    rows.append(
                        await run_case(
                            variant=variant,
                            scenario=scenario,
                            mode=mode,
                            timeout_seconds=timeout_seconds,
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
