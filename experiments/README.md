# Reitti Experiments

Academic experiment runner. Code kept small and readable.

Flow: `scenario -> matrix -> algorithm -> results.csv -> figures/summary`.

## Main Commands

From `experiments/`:

- `just sync`
- `just pipeline-fast-fixture`
- `just pipeline-fast-real`
- `just pipeline-fast-both`
- `just pipeline-full-fixture`
- `just pipeline-full-real`
- `just pipeline-full-both`
- `just clean-results`
- `just run-fast` (clean + pipeline-fast-both + plots/tables/docs)
- `just run-full` (clean + pipeline-full-both + plots/tables/docs)
- `just format` (ruff formatter)
- `just lint` (ruff checks)
- `just figures`
- `just summary-table`
- `just docs-report`

`pipeline-*` runs all useful experiment families (grid, ablation, boundary) and writes one unified output table.

## Pipeline Profiles

- `fast`: quick laptop run
  - fixture: reduced grid (`n=5,7,9,11` for A*, `n=5,6,7` for BF), profiles `relaxed/tight`, seed_count 1
  - real: same reduced grid logic, seed_count 1
  - boundary still included (infeasible + timeout behavior)
- `full`: stronger machine run
  - fixture: seed_count 10 for grid and ablation
  - real: full suite (grid + ablation + boundary)

## Data Modes

- `fixture`: synthetic matrix benchmark
- `real`: true Helsinki map stack (`graphhopper_gtfs`)
- `both`: execute both datasets in one run

## Output Files

- `outputs/results.csv` raw rows
- `outputs/raw/results.jsonl` raw jsonl
- `outputs/aggregated.csv` grouped stats
- `outputs/figures/*.png` plots
- `reports/summary.md` generated summary
- `../docs/experiments.md` generated final report

## Mode Safety

CSV contains:
- `mode` (`fixture` or `real`)
- `data_source` (`fixture_synthetic` or `graphhopper_gtfs`)

Compare by filtering on `mode`. For synthetic vs real comparison, use same `experiment` and `n_attractions`.

## Real-mode prerequisites

From repo root:

1. `just run`
2. `just prepare-postgis`
3. `cd experiments`
4. run one of `just pipeline-fast-real`, `just pipeline-fast-both`, `just pipeline-full-real`, `just pipeline-full-both`
