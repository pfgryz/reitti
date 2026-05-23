# Reitti Experiments

Academic experiment runner. Code kept small and readable.

Flow: `Hydra config -> scenarios -> matrix provider -> solver -> results.csv -> figures/summary`.

## Main Commands

From `experiments/`:

- `just sync`
- `uv run python -m experiments.app suite=synthetic_main setup=baseline`
- `uv run python -m experiments.app suite=heuristic_ablation setup=baseline`
- `uv run python -m experiments.app suite=bf_reference_small_n setup=window_stress`
- `uv run python -m experiments.app suite=handpicked_validation setup=infeasible_sanity`
- `uv run python -m experiments.app suite=real_reference setup=real_reference matrix.mode=real infra.database_url=... infra.graphhopper_base_url=...`
- `just clean-results`
- `just run-fast` (clean + pipeline-fast-both + plots/tables/docs)
- `just run-full` (clean + pipeline-full-both + plots/tables/docs)
- `just format` (ruff formatter)
- `just lint` (ruff checks)
- `just figures`
- `just summary-table`
- `just docs-report`

Each run appends rows to one unified output table. `just pipeline-*` wrappers still available for quick presets.

## Pipeline Profiles

- `fast`: quick laptop run
  - fixture:
    - `synthetic_main`: `n=[6,9]`, `profiles=[relaxed,tight]`, `seed_count=1`, `timeout=8`
    - `heuristic_ablation`: `n=[6,9]`, `profiles=[relaxed,tight]`, `seed_count=1`, `timeout=12`
    - `bf_reference_small_n`: `n=[6,8]`, `profiles=[relaxed,tight]`, `seed_count=1`, `timeout=20`
    - `handpicked_validation`: boundary cases, `timeout=20`
  - real:
    - `real_reference`: `n=[6,9]`, `seed_count=1`, `timeout=30`
  - objective: generate all plot inputs with short runtime
- `full`: stronger machine run
  - fixture: seed_count 10 for grid and ablation
  - real: full suite (grid + ablation + boundary)

## Core Concepts (for tutor defense)

### Scenario profiles (`relaxed`, `tight`, `impossible`)

Profiles control how attraction opening windows and stays are sampled in
`experiments/src/experiments/scenarios.py`.

- `relaxed`
  - windows sampled from setup baseline ranges (`open_start_*`, `window_len_*`)
  - usually feasible, good for normal scaling trends
- `tight`
  - windows shifted later and shortened (`+60..+120` start shift, `60..120` length)
  - harder scheduling, exposes pruning/search pressure
- `impossible`
  - windows near trip end and very short (`15..30` min)
  - stay lower bound forced up (`min_stay >= 30`)
  - intentionally drives `infeasible` outcomes

### Algorithm variants and what each proves

- `astar_greedy`
  - A* with greedy stay choice (`StaySelectionMode.GREEDY`)
  - practical fast baseline
- `astar_intervals`
  - A* with interval stay branching (`StaySelectionMode.INTERVALS_15_MIN`)
  - richer decision space, usually higher search cost
- `astar_intervals_no_heuristic`
  - same as `astar_intervals`, but heuristic disabled (`h=0`)
  - isolates heuristic impact
- `bruteforce_greedy`
  - DFS/exhaustive search (with pruning), greedy stays
  - tractable-size baseline
- `bruteforce_intervals`
  - DFS/exhaustive search (with pruning), interval stays
  - strongest reference on small `n`

### Main comparison semantics

- `heuristic_speedup = time(astar_intervals_no_heuristic) / time(astar_intervals)`
- `bf_objective` = matched brute-force objective for same
  `scenario_id + mode + stay_mode`
- `optimality_gap = (objective_cost - bf_objective) / bf_objective`
  - lower better
  - near `0` means A* close to brute-force reference

### Quality and objective

Quality values computed in `experiments/src/experiments/metrics/quality.py`:

- `total_stay_minutes`: total visit duration in route
- `stay_utilization`: fraction of maximum possible stay used
- `objective_cost`: optimization target used by solver
  - `objective = ALPHA * walk_distance + BETA * unused_stay_budget`
  - lower better

### Status meaning

- `ok`: feasible route found
- `infeasible`: constraints impossible
- `timeout`: computation exceeded timeout budget
- `failed`: runtime/system failure
- `skipped`: intentionally skipped (e.g. bruteforce above safety limit)

### `fixture` vs `real` mode

- `fixture`: synthetic travel matrices, controlled/cheap, trend-oriented
- `real`: backend multimodal stack (GraphHopper + GTFS + DB), expensive/realistic

Rule: compare fixture vs real as trend/ordering, not absolute milliseconds.

## Config map (`experiments/conf`)

### `config.yaml`
- Hydra root config
- chooses default `setup` and `suite`
- global knobs: `timeout_seconds`, `matrix`, `infra`, `output`

### `setup/*.yaml` (numeric scenario generators)
- `baseline`: default easy-ish ranges
- `window_stress`: narrow/tighter windows
- `network_stress`: broader stress ranges
- `infeasible_sanity`: impossible-oriented setup
- `real_reference`: setup used for real-mode reference runs

Each setup defines numeric ranges:
- time windows (`open_start_*`, `window_len_*`)
- stay bounds (`min_stay_*`, `extra_max_*`)
- base experiment grid defaults (`profiles`, `n_attractions`, `seed_count`)

### `suite/*.yaml` (what to run and why)
- `synthetic_main`
  - core fixture scaling trends
- `heuristic_ablation`
  - compares heuristic on/off directly
- `bf_reference_small_n`
  - small `n` quality/reference suite for A* vs brute-force
- `handpicked_validation`
  - curated boundary cases and expected statuses
- `real_reference`
  - real backend stack trend check

Suite fields:
- `variants`: algorithm list
- `n_attractions`, `seed_count`, `profiles`: scenario grid
- `matrix_mode`: default `fixture` or `real`
- `include_handpicked`, `handpicked_file` (for boundary suite)

### `handpicked/boundary.yaml`
- explicit boundary IDs:
  - `boundary_all_impossible`
  - `boundary_single_unreachable`
  - `boundary_empty_only_start`
  - `boundary_timeout_bf`
- used by `handpicked_validation`
- checked by feasibility metric rules

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
