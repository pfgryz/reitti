from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from .commands import (
    HANDLERS,
    run_ablation,
    run_boundary,
)
from .io_results import _write_outputs, output_dir_default
from .types import Row

__all__ = ["Row", "_write_outputs", "run_ablation", "run_boundary"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reitti-experiments")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(cmd: argparse.ArgumentParser) -> None:
        cmd.add_argument(
            "--matrix-mode", choices=["fixture", "real"], default="fixture"
        )
        cmd.add_argument("--output-dir", type=Path, default=output_dir_default())
        cmd.add_argument("--database-url", default=None)
        cmd.add_argument("--graphhopper-base-url", default=None)
        cmd.add_argument("--timeout-seconds", type=float, default=30.0)
        cmd.add_argument("--seed-count", type=int, default=10)

    for name in ("run-grid", "run-ablation", "run-boundary", "run-real-slice"):
        common(sub.add_parser(name))

    pipeline = sub.add_parser("run-pipeline")
    pipeline.add_argument("--output-dir", type=Path, default=output_dir_default())
    pipeline.add_argument("--database-url", default=None)
    pipeline.add_argument("--graphhopper-base-url", default=None)
    pipeline.add_argument("--timeout-seconds", type=float, default=30.0)
    pipeline.add_argument("--profile", choices=["fast", "full"], default="fast")
    pipeline.add_argument(
        "--data-mode",
        choices=["fixture", "real", "both"],
        default="fixture",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    rows = await HANDLERS[args.command](args)
    df = _write_outputs(output_dir=args.output_dir, rows=rows)
    counts = {
        k: int((df["status"] == k).sum()) if not df.empty else 0
        for k in ("ok", "infeasible", "timeout", "failed", "skipped")
    }
    print(
        f"saved {len(rows)} rows to {args.output_dir}/results.csv "
        f"(ok={counts['ok']}, infeasible={counts['infeasible']}, "
        f"timeout={counts['timeout']}, failed={counts['failed']}, "
        f"skipped={counts['skipped']})"
    )
    return 0 if counts["failed"] == 0 else 1


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
