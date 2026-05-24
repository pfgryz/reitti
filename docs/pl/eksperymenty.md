# Raport z eksperymentów

Wygenerowano automatycznie z plików `experiments/outputs/results.csv` oraz `experiments/outputs/aggregated.csv`.

## Konfiguracja

### Wymagania wstępne

- Środowisko Pythona zsynchronizowane w `experiments/` (`just sync`).
- Dla pomiarów na danych rzeczywistych (tryb `real`): uruchomiony i załadowany GraphHopper oraz PostGIS.

### Polecenia uruchomienia

- Główny zestaw na danych syntetycznych: `uv run python -m experiments.app suite=synthetic_main setup=baseline`
- Wpływ heurystyki (wariant z heurystyką i bez): `uv run python -m experiments.app suite=heuristic_ablation setup=baseline`
- Punkt odniesienia brute-force: `uv run python -m experiments.app suite=bf_reference_small_n setup=window_stress`
- Walidacja ręcznie dobranych scenariuszy: `uv run python -m experiments.app suite=handpicked_validation setup=infeasible_sanity`
- Punkt odniesienia na danych z Helsinek: `uv run python -m experiments.app suite=real_reference setup=real_reference matrix.mode=real infra.database_url=... infra.graphhopper_base_url=...`

## Jak czytać wykresy

- Każdy wykres skalowania ma panel profilu **relaxed** (luźne okno wycieczki) i **tight** (ciasne). Przy ciasnym oknie przeszukiwanie szybciej się kończy, więc wartości bezwzględne są znacznie mniejsze niż przy luźnym.
- Osie Y na wykresach skalowania są **logarytmiczne**. Spadek lub płaski odcinek blisko prawego brzegu krzywej zwykle oznacza, że algorytm trafił w limit czasu na trudniejszych scenariuszach (patrz adnotacja `ok/total`).
- **Pusty marker** z `k/n` obok oznacza, że tylko `k` z `n` przebiegów przy danym `n_attractions` zakończyło się w limicie czasu. Mediana na wykresie odzwierciedla więc tylko łatwiejsze przypadki i należy ją traktować jako dolne oszacowanie.
- Konkretnie: `bruteforce_intervals` ma szczyt około `n=9` (relaxed) i wygląda na *spadek* przy `n=10` wyłącznie dlatego, że 11 z 12 scenariuszy przekroczyło limit czasu przy `n=10` i przetrwał tylko najtańszy.

## Praktyczne wnioski

- A* z rozgałęzianiem po przedziałach pobytu dorównuje zachłannemu A* pod względem jakości i pozostaje wyraźnie poniżej jednej sekundy do `n_attractions = 12` na danych syntetycznych (patrz skalowanie czasu). Przy `n=15` profil relaxed staje się trudniejszy i w limicie czasu kończy się tylko profil tight.
- Pełne przeszukiwanie (brute-force) jako punkt odniesienia potwierdza, że A* jest optymalny w każdym rozwiązywalnym przypadku (patrz tabela luki optymalności poniżej: maksymalna luka to w praktyce szum zmiennoprzecinkowy).
- Pomiary na mapie i rozkładach HSL są zdominowane przez zapytania do GraphHoppera i PostGIS: czas wykonania jest rzędu około dwóch wielkości większy niż na danych syntetycznych przy tym samym `n_attractions`, podczas gdy samo przeszukiwanie rozwija tyle samo węzłów (patrz wykres real vs fixture).

## Główne tabele

### Status według trybu i eksperymentu

| mode | experiment | runs | ok | ok_rate |
| --- | --- | --- | --- | --- |
| fixture | astar_greedy | 220 | 205 | 0.932 |
| fixture | astar_intervals | 292 | 277 | 0.949 |
| fixture | astar_intervals_no_heuristic | 76 | 72 | 0.947 |
| fixture | bruteforce_greedy | 124 | 121 | 0.976 |
| fixture | bruteforce_intervals | 124 | 110 | 0.887 |
| real | astar_greedy | 9 | 9 | 1.0 |
| real | astar_intervals | 9 | 9 | 1.0 |

### Podsumowanie czasu i jakości

| mode | experiment | avg_ok_rate | avg_wall_time_ms | avg_expanded_nodes | avg_peak_memory_mb | median_objective_cost | avg_stay_utilization |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fixture | astar_greedy | 0.818 | 67.104 | 646.458 | 0.252 | 14913.794 | 1.0 |
| fixture | astar_intervals | 0.857 | 62.359 | 546.83 | 0.32 | 14913.794 | 1.0 |
| fixture | astar_intervals_no_heuristic | 0.692 | 1565.114 | 11709.844 | 74.998 | 14250.845 | 1.0 |
| fixture | bruteforce_greedy | 0.786 | 418.142 | 23144.75 | 4.101 | 13877.614 | 1.0 |
| fixture | bruteforce_intervals | 0.72 | 2561.584 | 141217.864 | 23.853 | 15270.08 | 1.0 |
| real | astar_greedy | 1.0 | 2755.717 | 533.0 | 3.612 | 2875.748 | 1.0 |
| real | astar_intervals | 1.0 | 2819.131 | 533.0 | 8.479 | 2875.748 | 1.0 |

### Luka optymalności względem brute-force (na algorytm / profil)

| experiment | profile | compared_cases | max_abs_gap | median_abs_gap |
| --- | --- | --- | --- | --- |
| astar_greedy | relaxed | 60 | 4.90e-03 | 0.00e+00 |
| astar_greedy | tight | 60 | 0.00e+00 | 0.00e+00 |
| astar_intervals | relaxed | 49 | 4.90e-03 | 0.00e+00 |
| astar_intervals | tight | 60 | 0.00e+00 | 0.00e+00 |

### Podsumowanie przyspieszenia heurystyki

| mode | mean_speedup_vs_no_heuristic | sample_count |
| --- | --- | --- |
| fixture | 85.143 | 144 |

### Podsumowanie poprawności wykonalności (ręcznie dobrane scenariusze brzegowe)

| mode | checked_cases | correct_cases | correct_rate |
| --- | --- | --- | --- |
| fixture | 17 | 16 | 0.941 |

## Wykresy końcowe

### Skalowanie czasu (dane syntetyczne)

![Skalowanie czasu (dane syntetyczne)](../figures/experiments/runtime_scaling.png)

### Skalowanie pamięci (dane syntetyczne)

![Skalowanie pamięci (dane syntetyczne)](../figures/experiments/memory_scaling.png)

### Czas: Helsinki vs dane syntetyczne

![Czas Helsinki vs dane syntetyczne](../figures/experiments/real_vs_fixture.png)

### Pamięć: Helsinki vs dane syntetyczne

![Pamięć Helsinki vs dane syntetyczne](../figures/experiments/real_vs_fixture_memory.png)


## Dodatek: wewnętrzne metryki przeszukiwania

Te wykresy opisują wewnętrzne działanie algorytmu (wysiłek przeszukiwania, porównanie z wariantem bez heurystyki), a nie czas widziany od strony aplikacji. Zostawione dla kompletności.

### Skalowanie rozwiniętych węzłów (dane syntetyczne)

![Skalowanie rozwiniętych węzłów (dane syntetyczne)](../figures/experiments/expanded_nodes_scaling.png)

### Wpływ heurystyki na czas (dane syntetyczne)

![Wpływ heurystyki na czas (dane syntetyczne)](../figures/experiments/heuristic_ablation.png)
