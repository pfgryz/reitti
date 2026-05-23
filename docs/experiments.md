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
| fixture | astar_greedy | 12 | 3 | 0.25 |
| fixture | astar_intervals | 16 | 10 | 0.625 |
| fixture | astar_intervals_no_heuristic | 8 | 4 | 0.5 |
| fixture | bruteforce_greedy | 12 | 3 | 0.25 |
| fixture | bruteforce_intervals | 12 | 6 | 0.5 |
| real | astar_greedy | 2 | 2 | 1.0 |
| real | astar_intervals | 2 | 2 | 1.0 |

### Runtime and quality summary

| mode | experiment | avg_ok_rate | avg_wall_time_ms | avg_expanded_nodes | avg_peak_memory_mb | median_objective_cost | avg_stay_utilization |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fixture | astar_greedy | 0.25 | 0.266 | 12.0 | 0.017 | 11048.863 | 1.0 |
| fixture | astar_intervals | 0.625 | 5.686 | 369.8 | 0.098 | 274117.276 | 0.799 |
| fixture | astar_intervals_no_heuristic | 0.5 | 11.645 | 289.5 | 0.688 | 11127.084 | 0.892 |
| fixture | bruteforce_greedy | 0.25 | 4.105 | 1163.0 | 0.159 | 11048.863 | 1.0 |
| fixture | bruteforce_intervals | 0.5 | 21.529 | 3065.333 | 0.406 | 842850.938 | 0.738 |
| real | astar_greedy | 1.0 | 1861.519 | 413.0 | 1.329 | 2836.348 | 1.0 |
| real | astar_intervals | 1.0 | 69.736 | 413.0 | 2.371 | 2836.348 | 1.0 |

### Heuristic speedup summary

| mode | mean_speedup_vs_no_heuristic | sample_count |
| --- | --- | --- |
| fixture | 7.494 | 8 |

### Feasibility correctness summary

| mode | checked_cases | correct_cases | correct_rate |
| --- | --- | --- | --- |
| fixture | 17 | 15 | 0.882 |

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

