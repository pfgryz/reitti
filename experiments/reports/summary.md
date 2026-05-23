# Experiment Summary

Generated from `outputs/aggregated.csv`.

```csv
experiment,n_attractions,profile,suite,setup_name,mode,run_count,ok_count,wall_time_ms_mean,wall_time_ms_std,expanded_nodes_mean,objective_cost_median,peak_memory_mb_mean,optimality_gap_mean,stay_utilization_mean
astar_greedy,1,relaxed,handpicked_validation,infeasible_sanity,fixture,1,1,0.0208749988814815,,1.0,0.0,0.001861572265625,,1.0
astar_greedy,6,relaxed,bf_reference_small_n,window_stress,fixture,1,0,0.0,,,,,,
astar_greedy,6,relaxed,handpicked_validation,infeasible_sanity,fixture,1,0,0.0,,,,,,
astar_greedy,6,relaxed,real_reference,real_reference,real,1,1,1186.747750001814,,8.0,2650.758,1.1792287826538086,,1.0
astar_greedy,6,relaxed,synthetic_main,baseline,fixture,1,1,1.5055829971970525,,14.0,11048.863137944629,0.0210418701171875,0.0,1.0
astar_greedy,6,tight,bf_reference_small_n,window_stress,fixture,1,0,0.0,,,,,,
astar_greedy,6,tight,synthetic_main,baseline,fixture,1,0,0.0,,,,,,
astar_greedy,8,impossible,handpicked_validation,infeasible_sanity,fixture,1,0,0.0,,,,,,
astar_greedy,8,relaxed,bf_reference_small_n,window_stress,fixture,1,0,0.0,,,,,,
astar_greedy,8,tight,bf_reference_small_n,window_stress,fixture,1,0,0.0,,,,,,
astar_greedy,9,relaxed,real_reference,real_reference,real,1,1,2536.2897500017425,,818.0,3021.938,1.4783363342285156,,1.0
astar_greedy,9,relaxed,synthetic_main,baseline,fixture,1,1,1.6619160014670342,,21.0,11205.305343268694,0.0271224975585937,0.0,1.0
astar_greedy,9,tight,synthetic_main,baseline,fixture,1,0,0.0,,,,,,
astar_greedy,10,relaxed,handpicked_validation,infeasible_sanity,fixture,1,0,0.0,,,,,,
astar_intervals,1,relaxed,handpicked_validation,infeasible_sanity,fixture,1,1,0.0116669980343431,,1.0,0.0,0.001861572265625,,1.0
astar_intervals,6,relaxed,bf_reference_small_n,window_stress,fixture,1,1,11.85408300079871,,422.0,537029.246280762,0.1522903442382812,0.0,0.8001941388858691
astar_intervals,6,relaxed,handpicked_validation,infeasible_sanity,fixture,1,0,0.0,,,,,,
astar_intervals,6,relaxed,heuristic_ablation,baseline,fixture,1,1,2.5318750012957025,,14.0,11048.863137944629,0.0598068237304687,,1.0
astar_intervals,6,relaxed,real_reference,real_reference,real,1,1,0.9517500002402812,,8.0,2650.758,0.02880859375,,1.0
astar_intervals,6,relaxed,synthetic_main,baseline,fixture,1,1,1.5552920012851246,,14.0,11048.863137944629,0.0499343872070312,0.0,1.0
astar_intervals,6,tight,bf_reference_small_n,window_stress,fixture,1,1,5.325166999682551,,281.0,1310859.531248738,0.0482254028320312,0.0,0.5062096600857826
astar_intervals,6,tight,heuristic_ablation,baseline,fixture,1,1,7.299624998267973,,296.0,1148672.6305351567,0.0560073852539062,,0.5688245812179327
astar_intervals,6,tight,synthetic_main,baseline,fixture,1,1,6.283874998189276,,296.0,1148672.6305351567,0.0555267333984375,0.0,0.5688245812179327
astar_intervals,8,impossible,handpicked_validation,infeasible_sanity,fixture,1,0,0.0,,,,,,
astar_intervals,8,relaxed,bf_reference_small_n,window_stress,fixture,1,1,50.07725000177743,,2332.0,1711326.8821082937,0.3992767333984375,0.0,0.5509236594848131
astar_intervals,8,tight,bf_reference_small_n,window_stress,fixture,1,0,0.0,,,,,,
astar_intervals,9,relaxed,heuristic_ablation,baseline,fixture,1,1,3.135874998406507,,21.0,11205.305343268694,0.0811920166015625,,1.0
astar_intervals,9,relaxed,real_reference,real_reference,real,1,1,138.51933399928384,,818.0,3021.938,4.7136688232421875,,1.0
astar_intervals,9,relaxed,synthetic_main,baseline,fixture,1,1,2.9020000001764856,,21.0,11205.305343268694,0.0802459716796875,,1.0
astar_intervals,9,tight,heuristic_ablation,baseline,fixture,1,0,0.0,,,,,,
astar_intervals,9,tight,synthetic_main,baseline,fixture,1,0,0.0,,,,,,
astar_intervals,10,relaxed,handpicked_validation,infeasible_sanity,fixture,1,0,0.0,,,,,,
astar_intervals_no_heuristic,1,relaxed,handpicked_validation,infeasible_sanity,fixture,1,1,0.0090829998953267,,1.0,0.0,0.0015487670898437,,1.0
astar_intervals_no_heuristic,6,relaxed,handpicked_validation,infeasible_sanity,fixture,1,0,0.0,,,,,,
astar_intervals_no_heuristic,6,relaxed,heuristic_ablation,baseline,fixture,1,1,6.888791998790111,,98.0,11048.863137944629,0.2479095458984375,,1.0
astar_intervals_no_heuristic,6,tight,heuristic_ablation,baseline,fixture,1,1,5.655375000060303,,296.0,1148672.6305351567,0.0521163940429687,,0.5688245812179327
astar_intervals_no_heuristic,8,impossible,handpicked_validation,infeasible_sanity,fixture,1,0,0.0,,,,,,
astar_intervals_no_heuristic,9,relaxed,heuristic_ablation,baseline,fixture,1,1,80.60329200088745,,763.0,11205.305343268694,2.4485092163085938,,1.0
astar_intervals_no_heuristic,9,tight,heuristic_ablation,baseline,fixture,1,0,0.0,,,,,,
astar_intervals_no_heuristic,10,relaxed,handpicked_validation,infeasible_sanity,fixture,1,0,0.0,,,,,,
```
