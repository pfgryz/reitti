from __future__ import annotations

import argparse
import shlex
import subprocess
import time


def _build_jobs() -> tuple[list[dict[str, object]], dict[str, object]]:
    fixture_jobs = [
        {
            "name": "synthetic_main",
            "command": [
                "uv",
                "run",
                "python",
                "-m",
                "experiments.app",
                "suite=synthetic_main",
                "setup=network_stress",
                "matrix.mode=fixture",
                "timeout_seconds=60",
                "output.output_dir=outputs/runs/synthetic_main",
            ],
        },
        {
            "name": "heuristic_ablation",
            "command": [
                "uv",
                "run",
                "python",
                "-m",
                "experiments.app",
                "suite=heuristic_ablation",
                "setup=baseline",
                "matrix.mode=fixture",
                "timeout_seconds=60",
                "output.output_dir=outputs/runs/heuristic_ablation",
            ],
        },
        {
            "name": "bf_reference_small_n",
            "command": [
                "uv",
                "run",
                "python",
                "-m",
                "experiments.app",
                "suite=bf_reference_small_n",
                "setup=window_stress",
                "matrix.mode=fixture",
                "timeout_seconds=60",
                "output.output_dir=outputs/runs/bf_reference_small_n",
            ],
        },
        {
            "name": "handpicked_validation",
            "command": [
                "uv",
                "run",
                "python",
                "-m",
                "experiments.app",
                "suite=handpicked_validation",
                "setup=infeasible_sanity",
                "matrix.mode=fixture",
                "timeout_seconds=60",
                "output.output_dir=outputs/runs/handpicked_validation",
            ],
        },
    ]
    real_job = {
        "name": "real_reference",
        "command": [
            "uv",
            "run",
            "python",
            "-m",
            "experiments.app",
            "suite=real_reference",
            "setup=real_reference",
            "matrix.mode=real",
            "infra.database_url=postgresql://admin:admin@localhost:5432/Reitti",
            "infra.graphhopper_base_url=http://localhost:8989",
            "timeout_seconds=90",
            "output.output_dir=outputs/runs/real_reference",
        ],
    }
    return fixture_jobs, real_job


def _format_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def _run_jobs_parallel(
    jobs: list[dict[str, object]], workers: int, dry_run: bool
) -> dict[str, int]:
    statuses: dict[str, int] = {}
    if dry_run:
        for job in jobs:
            name = str(job["name"])
            command = list(job["command"])
            print(f"[DRY-RUN] {name}: {_format_command(command)}")
            statuses[name] = 0
        return statuses

    pending = jobs[:]
    active: list[tuple[dict[str, object], subprocess.Popen[bytes]]] = []

    def _cleanup_children() -> None:
        if not active:
            return
        print("[CLEANUP] stopping active child processes...")
        for job, process in active:
            if process.poll() is not None:
                continue
            name = str(job["name"])
            print(f"[CLEANUP] terminate {name}")
            try:
                process.terminate()
            except ProcessLookupError:
                continue
        for _, process in active:
            if process.poll() is not None:
                continue
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass
        for job, process in active:
            if process.poll() is not None:
                continue
            name = str(job["name"])
            print(f"[CLEANUP] kill {name}")
            try:
                process.kill()
            except ProcessLookupError:
                continue
        for _, process in active:
            if process.poll() is not None:
                continue
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass

    try:
        while pending or active:
            while pending and len(active) < max(1, workers):
                job = pending.pop(0)
                name = str(job["name"])
                command = list(job["command"])
                print(f"[START] {name}: {_format_command(command)}")
                process = subprocess.Popen(command)
                active.append((job, process))

            next_active: list[tuple[dict[str, object], subprocess.Popen[bytes]]] = []
            for job, process in active:
                code = process.poll()
                if code is None:
                    next_active.append((job, process))
                    continue
                name = str(job["name"])
                statuses[name] = int(code)
                if code == 0:
                    print(f"[OK] {name}")
                else:
                    print(f"[FAIL] {name} exit={code}")
            active = next_active
            if active:
                time.sleep(0.2)
    except BaseException:
        _cleanup_children()
        raise

    return statuses


def _run_job_serial(job: dict[str, object], dry_run: bool) -> int:
    name = str(job["name"])
    command = list(job["command"])
    if dry_run:
        print(f"[DRY-RUN] {name}: {_format_command(command)}")
        return 0
    print(f"[START] {name}: {_format_command(command)}")
    result = subprocess.run(command, check=False)
    if result.returncode == 0:
        print(f"[OK] {name}")
    else:
        print(f"[FAIL] {name} exit={result.returncode}")
    return int(result.returncode)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run full suites with fixture jobs in parallel."
    )
    parser.add_argument("--workers", type=int, default=28)
    parser.add_argument(
        "--real-serial",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run real_reference only after fixture jobs finish.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    fixture_jobs, real_job = _build_jobs()

    if args.real_serial:
        fixture_statuses = _run_jobs_parallel(fixture_jobs, args.workers, args.dry_run)
        real_status = _run_job_serial(real_job, args.dry_run)
        failed = [name for name, code in fixture_statuses.items() if code != 0]
        if real_status != 0:
            failed.append(str(real_job["name"]))
        if failed:
            print(f"[SUMMARY] failed jobs: {', '.join(failed)}")
            return 1
        print("[SUMMARY] all jobs succeeded")
        return 0

    all_jobs = fixture_jobs + [real_job]
    statuses = _run_jobs_parallel(all_jobs, args.workers, args.dry_run)
    failed = [name for name, code in statuses.items() if code != 0]
    if failed:
        print(f"[SUMMARY] failed jobs: {', '.join(failed)}")
        return 1
    print("[SUMMARY] all jobs succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
