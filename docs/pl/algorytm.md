## Dane wejściowe
- $P = \{p_0, p_1, \ldots, p_n\}$ — zbiór atrakcji do odwiedzenia
- $p_0$ — punkt początkowy wycieczki (ustalony, odwiedzony na starcie)
- $[\mathrm{open}_i, \mathrm{close}_i]$ — godziny otwarcia atrakcji $i$
- $[\mathrm{min\_stay}_i, \mathrm{max\_stay}_i]$ — przedział czasu pobytu w atrakcji $i$
- $\mathit{start\_time}$ — czas rozpoczęcia wycieczki
- $\mathit{end\_time}$ — czas zakończenia wycieczki (domyślnie zamknięcie ostatniej odwiedzonej atrakcji)

### Wstępnie wyliczone dane

- $t^{\mathrm{pieszo}}_{ij}$ — czas przejścia pieszo z $i$ do $j$ (GraphHopper, OSM)
- $t^{\mathrm{km}}_{ij}$ — czas przejazdu komunikacją miejską (KM) z $i$ do $j$ (GTFS, HSL):
  - wybór najbliższego przystanku w promieniu 10 min pieszo od $i$
  - wybór najbliższego przystanku w promieniu 10 min pieszo od $j$
  - wybór pary przystanków ze średnim czasem przejazdu (najszybsze połączenie)
  - $t^{\mathrm{km}}_{ij} = t_{\mathrm{walk\_to\_stop}} + t_{\mathrm{transit}} + t_{\mathrm{walk\_from\_stop}}$
- $d_{ij}$ — dystans pieszy przebyty przy przejściu z $i$ do $j$ (w metrach)

**Wybór trybu przejazdu dla każdej pary $(i, j)$:**

$$
\mathit{travel\_time}_{ij} = \min(t^{\mathrm{pieszo}}_{ij},\, t^{\mathrm{km}}_{ij})
$$

$$
\mathit{walk\_dist}_{ij} =
\begin{cases}
d(i, \mathrm{stop}_a) + d(\mathrm{stop}_b, j) & \text{gdy KM jest szybsza} \\
d_{ij} & \text{gdy pieszo jest szybsze}
\end{cases}
$$
> Komunikacja miejska jest modelowana przez średni czas przejazdu między przystankami. Przyjmujemy, że autobus lub tramwaj jest dostępny natychmiast po dojściu do przystanku — pomijamy czas oczekiwania na pojazd.

## Stan


$$
s = (u,\, \mathit{Visited},\, t)
$$

- $u$ — obecna atrakcja (indeks do $P$)
- $\mathit{Visited}$ — zbiór odwiedzonych atrakcji (reprezentacja: bitmask)
- $t$ — aktualny czas (moment wyjścia z atrakcji $u$)

### Wyliczenia poza stanem

- $\mathit{d\_so\_far}$ — sumaryczny dystans pieszy dotychczasowej trasy
- $\mathit{unused\_so\_far} = \sum_{i \in \mathit{Visited}} (\mathrm{max\_stay}_i - \mathrm{stay}_i)$ — sumaryczny niewykorzystany czas pobytu

Nie wchodzą do klucza stanu $(u, V, t)$.

## Zmienne decyzyjne

- $t_{\mathrm{arr}}(i)$ — czas przybycia do atrakcji $i$
- $t_{\mathrm{dep}}(i)$ — czas odjazdu z atrakcji $i$
- $\mathrm{stay}_i = t_{\mathrm{dep}}(i) - t_{\mathrm{arr}}(i)$ — czas pobytu w atrakcji $i$

**Wariant zachłanny (deterministyczny):**

$$
\mathrm{stay}_i = \min\bigl(\mathrm{max\_stay}_i,\; \mathrm{close}_i - t_{\mathrm{arr}}(i),\; \mathit{end\_time} - t_{\mathrm{arr}}(i)\bigr)
$$

**Wariant z interwałami 15 min (rozgałęzienie decyzyjne):**

$$
\mathrm{stay}_i \in \{\mathrm{min\_stay}_i,\; \mathrm{min\_stay}_i + 15,\; \ldots,\; \mathrm{stay}_{\text{zachłanny}}\}
$$
## Odcinanie

Dla rozważanej atrakcji $w$ z bieżącego stanu $s = (u, V, t)$:

1. Zdążymy dojechać przed zamknięciem:
   $$
   t + \mathit{travel\_time}_{uw} \le \mathrm{close}_w
   $$
2. Zdążymy odbyć minimalny pobyt przed zamknięciem (uwzględniając oczekiwanie na otwarcie):
   $$
   \max(t + \mathit{travel\_time}_{uw},\, \mathrm{open}_w) + \mathrm{min\_stay}_w \le \mathrm{close}_w
   $$
3. Wycieczka skończy się na czas:
   $$
   \max(t + \mathit{travel\_time}_{uw},\, \mathrm{open}_w) + \mathrm{min\_stay}_w \le \mathit{end\_time}
   $$

Jeżeli którykolwiek warunek nie jest spełniony — przejście do $w$ jest odcinane.

## Funkcja kosztu

$$
g(s) = \alpha \cdot \mathit{d\_so\_far} + \beta \cdot \mathit{unused\_so\_far}
$$

gdzie:

- $\mathit{d\_so\_far} = \sum_{(i,j) \in \mathrm{route}} \mathit{walk\_dist}_{ij}$
- $\mathit{unused\_so\_far} = \sum_{i \in \mathit{Visited}} (\mathrm{max\_stay}_i - \mathrm{stay}_i)$

Wagi: $\beta \gg \alpha$ — priorytet leksykograficzny (najpierw maksymalizacja czasu pobytu, potem minimalizacja dystansu).

Wartości domyślne: $\alpha = 1{,}0$ (metr), $\beta = 10000{,}0$ (minuta niewykorzystanego pobytu).

## Funkcja heurystyczna


$$
h(s) = h_{\mathrm{dist}}(s) + h_{\mathrm{stay}}(s)
$$

### Składnik dystansu

$$
h_{\mathrm{dist}}(s) = \alpha \cdot \mathrm{MST\_weight}(\mathit{Unvisited} \cup \{u\},\, \mathit{walk\_dist})
$$

MST to minimalne drzewo spinające na pozostałych atrakcjach (plus bieżąca) z wagami równymi dystansom pieszym.

### Składnik czasu pobytu

$$
h_{\mathrm{stay}}(s) = 0
$$

**Eksperymentalne:**

$$
h_{\mathrm{stay}}(s) = \beta \cdot \sum_{i \in \mathit{Unvisited}} \max\bigl(0,\; \mathrm{max\_stay}_i - (\mathrm{close}_i - t^{\min}_{\mathrm{arr},\,i})\bigr)
$$

## Funkcja A*

$$
f(s) = g(s) + h(s)
$$
## Przejście

Dla $s = (u, V, t)$ i kandydata $w \notin V$:

1. $\mathit{travel\_t} = \mathit{travel\_time}_{uw}$, $\mathit{walk\_d} = \mathit{walk\_dist}_{uw}$ 
2. $t_{\mathrm{arr}} = t + \mathit{travel\_t}$
3. Jeśli $t_{\mathrm{arr}} < \mathrm{open}_w$: $t_{\mathrm{arr}} \leftarrow \mathrm{open}_w$ (czekanie, bez kary)
4. Sprawdź ograniczenia z sekcji Odcinanie. Jeśli naruszone - odetnij.
5. Wybór długości pobytu (zachłanny lub interwały 15 min)
6. Następnik: $s' = (w,\; V \cup \{w\},\; t_{\mathrm{arr}} + \mathrm{stay}_w)$
7. Akumulacja:
   - $\mathit{d\_so\_far} \mathrel{+}= \mathit{walk\_d}$
   - $\mathit{unused\_so\_far} \mathrel{+}= (\mathrm{max\_stay}_w - \mathrm{stay}_w)$

## Wykrycie braku rozwiązania

**Sprawdzenie wstępne (przed A*)**

- Dla każdej atrakcji $i$: sprawdź, czy istnieje jakikolwiek wykonalny czas przyjazdu $t_{\mathrm{arr}} \ge \mathrm{open}_i$ spełniający $t_{\mathrm{arr}} + \mathrm{min\_stay}_i \le \min(\mathrm{close}_i, \mathit{end\_time})$. Jeśli nie — atrakcja $i$ jest indywidualnie niewykonalna.

**Po nieudanym A***

- Pusta kolejka priorytetowa przed osiągnięciem stanu końcowego → problem niewykonalny.


## Optymalizacje funkcji $f(s)$

- Cachowanie MST po masce $\mathit{Unvisited}$
- W każdym kroku potrzebujemy wyliczyć $\mathrm{MST}(\mathit{Unvisited} \cup \{u\})$ w cache mając $\mathrm{MST}(\mathit{Unvisited})$ (własność cięcia MST)
  $$
\mathrm{MST}(S \cup \{u\}) = \mathrm{MST}(S) + \min_{v \in S} \mathit{walk\_dist}_{uv}
$$
- Cachowanie optymalnej ścieżki do stanu $s$: jeśli dwie różne ścieżki prowadzą do identycznego stanu $s = (u, V, t)$, przyszłe opcje z $s$ są identyczne dla obu -> zachowujemy najtańszą. Słownik `best_g`: `dict[state → float]`. Nowy stan dodajemy do kolejki tylko, jeśli $g_{\mathrm{new}} < \texttt{best\_g}[\mathit{state}]$. W przeciwnym razie odrzucamy go.
- Przed dodaniem następnika do kolejki sprawdzamy ograniczenia czasowe. Jeśli $t_{\mathrm{arr}} + \mathrm{min\_stay}_w > \mathrm{close}_w$ lub $> \mathit{end\_time}$, krawędź jest odrzucona przed policzeniem heurystyki.