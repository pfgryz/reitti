from __future__ import annotations

import asyncio
import multiprocessing as mp
import queue
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
WORKER_STARTUP_GRACE_SECONDS = 2.0


async def _run_case_with_provider(
    *,
    variant: Variant,
    scenario: Scenario,
    mode: str,
    timeout_seconds: float,
    astar_timeout_seconds: float | None,
    matrix_provider: MatrixProvider,
) -> Row:
    async with matrix_provider.acquire(scenario) as matrices:
        return await run_case(
            variant=variant,
            scenario=scenario,
            mode=mode,
            timeout_seconds=timeout_seconds,
            astar_timeout_seconds=astar_timeout_seconds,
            matrices=matrices,
        )


def _case_worker_entry(
    result_queue: mp.Queue,
    started_event: mp.synchronize.Event,
    *,
    variant: Variant,
    scenario: Scenario,
    mode: str,
    timeout_seconds: float,
    astar_timeout_seconds: float | None,
    matrix_provider: MatrixProvider,
) -> None:
    try:
        started_event.set()
        row = asyncio.run(
            _run_case_with_provider(
                variant=variant,
                scenario=scenario,
                mode=mode,
                timeout_seconds=timeout_seconds,
                astar_timeout_seconds=astar_timeout_seconds,
                matrix_provider=matrix_provider,
            )
        )
        result_queue.put(("ok", row))
    except Exception as exc:
        result_queue.put(("error", str(exc)))


def _run_case_hard_timeout(
    *,
    variant: Variant,
    scenario: Scenario,
    mode: str,
    timeout_seconds: float,
    astar_timeout_seconds: float | None,
    matrix_provider: MatrixProvider,
) -> Row:
    context = mp.get_context("spawn")
    result_queue: mp.Queue = context.Queue(maxsize=1)
    started_event = context.Event()
    process = context.Process(
        target=_case_worker_entry,
        kwargs={
            "result_queue": result_queue,
            "started_event": started_event,
            "variant": variant,
            "scenario": scenario,
            "mode": mode,
            "timeout_seconds": timeout_seconds,
            "astar_timeout_seconds": astar_timeout_seconds,
            "matrix_provider": matrix_provider,
        },
    )
    try:
        process.start()
        if not started_event.wait(timeout=WORKER_STARTUP_GRACE_SECONDS):
            if process.is_alive():
                process.terminate()
                process.join(1.0)
                if process.is_alive():
                    process.kill()
                    process.join(1.0)
            return row_error(
                variant=variant,
                scenario=scenario,
                mode=mode,
                status="failed",
                error="worker failed to start case execution",
            )

        process.join(timeout_seconds)
        if process.is_alive():
            process.terminate()
            process.join(1.0)
            if process.is_alive():
                process.kill()
                process.join(1.0)
            return row_error(
                variant=variant,
                scenario=scenario,
                mode=mode,
                status="timeout",
                error=f"case timed out after {timeout_seconds:.1f}s (hard kill)",
            )

        payload: tuple[str, object] | None = None
        try:
            payload = result_queue.get_nowait()
        except queue.Empty:
            payload = None

        if payload is None:
            return row_error(
                variant=variant,
                scenario=scenario,
                mode=mode,
                status="failed",
                error=f"worker exited with code {process.exitcode}",
            )

        kind, value = payload
        if kind == "ok":
            return value  # type: ignore[return-value]
        return row_error(
            variant=variant,
            scenario=scenario,
            mode=mode,
            status="failed",
            error=str(value),
        )
    finally:
        result_queue.close()
        result_queue.join_thread()


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
    suite_timeout_warned = False
    started = time.monotonic()
    for scenario in scenarios:
        bar.set_description(f"{desc}:n={scenario.n_attractions}")
        for variant in variants:
            if (
                suite_timeout_seconds is not None
                and not suite_timeout_warned
                and time.monotonic() - started >= suite_timeout_seconds
            ):
                print(
                    f"[SUITE-TIMEOUT-SOFT] {desc} exceeded {suite_timeout_seconds:.1f}s; continuing per-case timeouts."
                )
                suite_timeout_warned = True

            rows.append(
                await asyncio.to_thread(
                    _run_case_hard_timeout,
                    variant=variant,
                    scenario=scenario,
                    mode=mode,
                    timeout_seconds=timeout_seconds,
                    astar_timeout_seconds=astar_timeout_seconds,
                    matrix_provider=matrix_provider,
                )
            )
            bar.update(1)
    bar.close()
    return rows
