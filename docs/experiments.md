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
| fixture | astar_greedy | 220 | 18 | 0.082 |
| fixture | astar_intervals | 220 | 47 | 0.214 |
| fixture | astar_intervals_no_heuristic | 4 | 1 | 0.25 |
| fixture | bruteforce_greedy | 124 | 3 | 0.024 |
| fixture | bruteforce_intervals | 124 | 16 | 0.129 |
| real | astar_greedy | 9 | 6 | 0.667 |
| real | astar_intervals | 9 | 6 | 0.667 |

### Runtime and quality summary

| mode | experiment | avg_ok_rate | avg_wall_time_ms | avg_expanded_nodes | avg_peak_memory_mb | median_objective_cost | avg_stay_utilization |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fixture | astar_greedy | 0.11 | 0.692 | 308.68 | 0.069 | 247176.012 | 0.917 |
| fixture | astar_intervals | 0.22 | 34726.317 | 1472392.875 | 342.493 | 1246062.554 | 0.68 |
| fixture | astar_intervals_no_heuristic | 0.25 | 0.002 | 1.0 | 0.002 | 0.0 | 1.0 |
| fixture | bruteforce_greedy | 0.083 | 0.006 | 28.667 | 0.004 | 247176.012 | 0.899 |
| fixture | bruteforce_intervals | 0.161 | 0.818 | 889.606 | 0.079 | 1038154.165 | 0.679 |
| real | astar_greedy | 0.667 | 1286.679 | 457.5 | 1.509 | 3312.438 | 1.0 |
| real | astar_intervals | 0.667 | 1235.884 | 457.5 | 3.356 | 3312.438 | 1.0 |

### Heuristic speedup summary

| mode | mean_speedup_vs_no_heuristic | sample_count |
| --- | --- | --- |
| fixture | 0.684 | 2 |

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

### Feasibility Matrix

![feasibility matrix](figures/experiments/feasibility_matrix.png)

### Real Vs Fixture

![real vs fixture](figures/experiments/real_vs_fixture.png)

