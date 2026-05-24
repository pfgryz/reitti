from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import hydra
from omegaconf import DictConfig, OmegaConf

from .executor import run_suite
from .io_results import _write_outputs, output_dir_default
from .matrices import (
    FixtureMatrixConfig,
    FixtureMatrixProvider,
    RealMatrixProvider,
)
from .scenarios import build_scenarios, setup_from_dict, suite_from_dict
from .types import ALL_VARIANTS


def _fixture_config(cfg: DictConfig) -> FixtureMatrixConfig:
    matrix_cfg = cfg.get("matrix", {})
    return FixtureMatrixConfig(
        density=float(matrix_cfg.get("density", 1.0)),
        disconnected_prob=float(matrix_cfg.get("disconnected_prob", 0.0)),
        time_min=float(matrix_cfg.get("time_min", 5.0)),
        time_max=float(matrix_cfg.get("time_max", 45.0)),
        pt_faster_prob=float(matrix_cfg.get("pt_faster_prob", 0.35)),
        pt_speedup_min=float(matrix_cfg.get("pt_speedup_min", 1.05)),
        pt_speedup_max=float(matrix_cfg.get("pt_speedup_max", 1.80)),
    )


async def _run(cfg: DictConfig) -> int:
    # Silence per-request transport logs during experiment batches.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    setup_name = str(cfg.get("setup_name"))
    suite_name = str(cfg.get("suite_name", cfg.get("suite", {}).get("name", "suite")))
    setup_cfg = setup_from_dict(
        OmegaConf.to_container(cfg.setup, resolve=True),  # type: ignore[arg-type]
        name=setup_name,
    )
    suite_cfg = suite_from_dict(
        OmegaConf.to_container(cfg.suite, resolve=True),  # type: ignore[arg-type]
        name=suite_name,
    )
    fixture_cfg = _fixture_config(cfg)
    scenarios = build_scenarios(
        setup=setup_cfg, suite=suite_cfg, fixture_cfg=fixture_cfg
    )
    variants = [ALL_VARIANTS[name] for name in suite_cfg.variants]
    timeout_seconds = float(cfg.get("timeout_seconds", 60.0))
    astar_timeout_seconds = float(cfg.get("astar_timeout_seconds", 60.0))
    suite_timeout_seconds_cfg = cfg.get("suite_timeout_seconds", None)
    suite_timeout_seconds = (
        None
        if suite_timeout_seconds_cfg is None
        else float(suite_timeout_seconds_cfg)
    )

    mode = str(cfg.get("matrix", {}).get("mode", suite_cfg.matrix_mode))
    if mode == "real":
        matrix_provider = RealMatrixProvider(
            database_url=cfg.get("infra", {}).get("database_url"),
            graphhopper_base_url=cfg.get("infra", {}).get("graphhopper_base_url"),
        )
    else:
        matrix_provider = FixtureMatrixProvider(fixture_cfg)

    rows = await run_suite(
        scenarios=scenarios,
        variants=variants,
        mode=mode,
        timeout_seconds=timeout_seconds,
        astar_timeout_seconds=astar_timeout_seconds,
        suite_timeout_seconds=suite_timeout_seconds,
        matrix_provider=matrix_provider,
        desc=f"{suite_name}:{setup_name}",
    )
    output_dir = Path(
        str(cfg.get("output", {}).get("output_dir", output_dir_default()))
    )
    df = _write_outputs(output_dir=output_dir, rows=rows)
    failed_count = int((df["status"] == "failed").sum()) if not df.empty else 0
    print(f"saved {len(rows)} rows to {output_dir}/results.csv")
    return 0 if failed_count == 0 else 1


@hydra.main(version_base=None, config_path="../../conf", config_name="config")
def main(cfg: DictConfig) -> None:
    raise SystemExit(asyncio.run(_run(cfg)))


if __name__ == "__main__":
    main()
