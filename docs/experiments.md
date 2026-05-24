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

## Experiment Justification

- **A* greedy vs A* intervals**: checks quality/runtime trade-off from richer stay-time branching.
- **Ablation (heuristic off)**: isolates value of heuristic guidance in search speed.
- **Brute-force baseline**: provides reference objective for small/feasible cases.
- **Boundary cases**: verifies infeasible/timeout handling and robustness.
- **Synthetic vs real matrices**: tests if trends hold when using true Helsinki routing stack.

## Key Tables

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

### Heuristic speedup summary

| mode | mean_speedup_vs_no_heuristic | sample_count |
| --- | --- | --- |
| fixture | 85.143 | 144 |

### Feasibility correctness summary

| mode | checked_cases | correct_cases | correct_rate |
| --- | --- | --- | --- |
| fixture | 17 | 16 | 0.941 |

## Final Plots

### Runtime Scaling

![runtime scaling](figures/experiments/runtime_scaling.png)

### Expanded Nodes Scaling

![expanded nodes scaling](figures/experiments/expanded_nodes_scaling.png)

### Memory Scaling

![memory scaling](figures/experiments/memory_scaling.png)

### Quality Boxplot

![quality boxplot](figures/experiments/quality_boxplot.png)

### Optimality Gap

![optimality gap](figures/experiments/optimality_gap.png)

### Heuristic Ablation

![heuristic ablation](figures/experiments/heuristic_ablation.png)

### Feasibility Matrix

![feasibility matrix](figures/experiments/feasibility_matrix.png)

### Real Vs Fixture

![real vs fixture](figures/experiments/real_vs_fixture.png)

