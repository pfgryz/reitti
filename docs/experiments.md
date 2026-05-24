# Experiments Report

Generated automatically from `experiments/outputs/results.csv` and `experiments/outputs/aggregated.csv`.

## Setup

### Prerequisites
- Python env synced in `experiments/` (`just sync`).
- For real-mode runs: GraphHopper + PostGIS started and loaded.

### Run commands
- Synthetic main: `uv run python -m experiments.app suite=synthetic_main setup=baseline`
- Heuristic ablation: `uv run python -m experiments.app suite=heuristic_ablation setup=baseline`
- BF reference: `uv run python -m experiments.app suite=bf_reference_small_n setup=window_stress`
- Handpicked validation: `uv run python -m experiments.app suite=handpicked_validation setup=infeasible_sanity`
- Real reference: `uv run python -m experiments.app suite=real_reference setup=real_reference matrix.mode=real infra.database_url=... infra.graphhopper_base_url=...`

## Reading the figures

- Each scaling figure has a **relaxed** and **tight** profile panel (time-window pressure). Tight windows prune the search aggressively, so absolute numbers stay much smaller than under relaxed windows.
- Y-axes are **logarithmic** on scaling plots. A drop or plateau near the right edge of a curve usually means the algorithm hit the timeout on the harder scenarios (see `ok/total` annotation).
- A **hollow marker** with `k/n` next to it means only `k` out of `n` runs at that `n_attractions` finished within the timeout. The plotted median therefore reflects only the easier survivors and should be read as a lower bound.
- Concretely: `bruteforce_intervals` peaks around `n=9` relaxed and appears to *drop* at `n=10` purely because 11 of 12 scenarios timed out at `n=10` and only the cheapest one survived.

## Practical takeaways

- A* with the interval branching matches greedy A* on quality and stays well under one second up to `n_attractions = 12` on synthetic fixtures (see runtime scaling). At `n=15` the relaxed profile becomes the harder regime and only the tight profile finishes.
- Brute-force baselines confirm A* is optimal on every solvable case (see optimality-gap table below: max gap is essentially floating-point noise).
- Real Helsinki-stack runs are dominated by GraphHopper / PostGIS round-trips: walltime is roughly two orders of magnitude above the synthetic fixture for the same `n_attractions`, while the search itself expands the same number of nodes (see real-vs-fixture).

## Key tables

### Status by mode and experiment

| mode | experiment | runs | ok | ok_rate |
| --- | --- | --- | --- | --- |
| fixture | astar_greedy | 220 | 205 | 0.932 |
| fixture | astar_intervals | 292 | 277 | 0.949 |
| fixture | astar_intervals_no_heuristic | 76 | 72 | 0.947 |
| fixture | bruteforce_greedy | 124 | 121 | 0.976 |
| fixture | bruteforce_intervals | 124 | 110 | 0.887 |
| real | astar_greedy | 9 | 9 | 1.0 |
| real | astar_intervals | 9 | 9 | 1.0 |

### Runtime and quality summary

| mode | experiment | avg_ok_rate | avg_wall_time_ms | avg_expanded_nodes | avg_peak_memory_mb | median_objective_cost | avg_stay_utilization |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fixture | astar_greedy | 0.818 | 67.104 | 646.458 | 0.252 | 14913.794 | 1.0 |
| fixture | astar_intervals | 0.857 | 62.359 | 546.83 | 0.32 | 14913.794 | 1.0 |
| fixture | astar_intervals_no_heuristic | 0.692 | 1565.114 | 11709.844 | 74.998 | 14250.845 | 1.0 |
| fixture | bruteforce_greedy | 0.786 | 418.142 | 23144.75 | 4.101 | 13877.614 | 1.0 |
| fixture | bruteforce_intervals | 0.72 | 2561.584 | 141217.864 | 23.853 | 15270.08 | 1.0 |
| real | astar_greedy | 1.0 | 2755.717 | 533.0 | 3.612 | 2875.748 | 1.0 |
| real | astar_intervals | 1.0 | 2819.131 | 533.0 | 8.479 | 2875.748 | 1.0 |

### Optimality gap vs brute-force (per algorithm / profile)

| experiment | profile | compared_cases | max_abs_gap | median_abs_gap |
| --- | --- | --- | --- | --- |
| astar_greedy | relaxed | 60 | 4.90e-03 | 0.00e+00 |
| astar_greedy | tight | 60 | 0.00e+00 | 0.00e+00 |
| astar_intervals | relaxed | 49 | 4.90e-03 | 0.00e+00 |
| astar_intervals | tight | 60 | 0.00e+00 | 0.00e+00 |

### Heuristic speedup summary

| mode | mean_speedup_vs_no_heuristic | sample_count |
| --- | --- | --- |
| fixture | 85.143 | 144 |

### Feasibility correctness summary (handpicked boundary suite)

| mode | checked_cases | correct_cases | correct_rate |
| --- | --- | --- | --- |
| fixture | 17 | 16 | 0.941 |

## Final plots

### Runtime scaling (fixture)

![Runtime scaling (fixture)](figures/experiments/runtime_scaling.png)

### Memory scaling (fixture)

![Memory scaling (fixture)](figures/experiments/memory_scaling.png)

### Real vs fixture runtime

![Real vs fixture runtime](figures/experiments/real_vs_fixture.png)

### Real vs fixture memory

![Real vs fixture memory](figures/experiments/real_vs_fixture_memory.png)


## Appendix: internal search metrics

These figures describe algorithm internals (search effort, heuristic ablation) rather than user-facing performance. They are kept for completeness.

### Expanded nodes scaling (fixture)

![Expanded nodes scaling (fixture)](figures/experiments/expanded_nodes_scaling.png)

### Heuristic ablation runtime (fixture)

![Heuristic ablation runtime (fixture)](figures/experiments/heuristic_ablation.png)

