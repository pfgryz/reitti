# Dokumentacja Reitti

## Spis treści

1. [Architektura](#architektura)
2. [Instrukcja](#instrukcja)
3. [Założenia](#założenia)
4. [Algorytm](#algorytm)
5. [Implementacja](#implementacja)
6. [Eksperymenty](#eksperymenty)

---

## Architektura

**Reitti** służy do planowania jednodniowej wycieczki po Helsinkach: użytkownik podaje punkt startowy, atrakcje z godzinami otwarcia i ramy czasowe, a system proponuje kolejność odwiedzin oraz szacunkowe czasy i dystanse dojazdów. Szczegóły obliczeń są w sekcjach [Algorytm](#algorytm) i [Założenia](#założenia).

Aplikacja składa się z interfejsu w przeglądarce, serwera aplikacji oraz dwóch usług uruchamianych w Dockerze: bazy danych z rozkładami jazdy i silnika tras pieszych.

### Diagram

```mermaid
flowchart TB
    U(["Użytkownik"])

    subgraph FE["Frontend"]
        UI["Interfejs: mapa,<br/>lista atrakcji"]
    end

    subgraph BE["Backend"]
        API["Zapytania z interfejsu"]
        CORE["Planowanie trasy"]
        API --> CORE
    end

    GH["GraphHopper<br/>trasy piesze"]
    PG["PostGIS<br/>komunikacja miejska HSL"]

    U --> UI
    UI --> API
    BE -->|"strona aplikacji"| UI
    CORE --> GH
    CORE --> PG
```

Użytkownik wchodzi pod jeden adres (np. `http://127.0.0.1:8000/app/`). Backend obsługuje zarówno stronę aplikacji, jak i zapytania o trasy, przystanki i optymalizację wycieczki.

### Frontend

Warstwa widoczna dla użytkownika jest napisana w **Vue.js** (Pinia). Pokazuje mapę, formularz wycieczki (start, godziny, dzień tygodnia, atrakcje z czasem pobytu) oraz wynik na mapie.

Lista miejsc do wyboru pochodzi z **`GET /places`**. Optymalizacja: **`POST /trip/optimize`** z punktem startowym jako `attractions[0]` i geometrią odcinków (`include_legs`). Kontrakt HTTP: [Implementacja](#implementacja). Instalacja: [Instrukcja](#instrukcja).

### Backend

Serwer w **Pythonie** to centrum systemu:

- liczy czasy dojazdu (pieszo i komunikacją miejską), wyszukuje przystanki i **ustala optymalną kolejność odwiedzin** ([Algorytm](#algorytm)),
- udostępnia interfejs pod adresem `/app/`.

### PostGIS

Baza **PostgreSQL z rozszerzeniem PostGIS** przechowuje dane **GTFS** helsińskiego operatora HSL: przystanki, linie, czasy przejazdów. Na tej podstawie backend szacuje dojazdy komunikacją miejską (m.in. średnie czasy między parami przystanków). Dane ładuje się skryptami z `backend/db/migrations/` po starcie kontenerów.

### GraphHopper

Osobna usługa liczy **trasy piesze** na mapie OpenStreetMap (dystans, czas). Backend odpytuje ją przy każdym odcinku pieszym. Parametry profilu pieszego (prędkość, schody, kierunek startu) — w [Założeniach](#założenia).

### Przykładowy przepływ

Użytkownik ustawia start, godziny wycieczki i kilka atrakcji, potem klika wyznaczenie trasy:

1. Interfejs przekazuje dane do serwera.
2. Serwer liczy czasy dojazdów (GraphHopper, baza HSL) i wybiera kolejność odwiedzin.
3. Użytkownik widzi łączny czas wycieczki i trasę na mapie.

Instalacja: [Instrukcja](#instrukcja).

---

## Instrukcja

### Wymagania

- [Docker](https://docs.docker.com/get-docker/)
- [just](https://github.com/casey/just)
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+

Pierwsze `just setup` pobiera mapę OSM i rozkłady jazdy HSL - pliki są duże; potrzebne jest połączenie z internetem i kilka gigabajtów wolnego miejsca.

### Instalacja

Wykonaj polecenia w katalogu głównym repozytorium (kolejność ma znaczenie).

1. **Dane projektu** - pobranie mapy i rozkładów jazdy:
   ```sh
   just setup
   ```

2. **Usługi w tle** - baza PostGIS i GraphHopper:
   ```sh
   just run
   ```
   Przy pierwszym starcie GraphHopper przetwarza mapę OSM; może to potrwać kilkanaście minut. Status: `docker compose ps`.

3. **Baza** - utworzenie tabel i załadowanie danych (kontenery muszą już działać):
   ```sh
   just prepare-postgis
   ```

4. **Konfiguracja serwera** - skopiuj `backend/.env.example` do `backend/.env`:
   ```env
   DATABASE_URL=postgresql://admin:admin@localhost:5432/Reitti
   GRAPHHOPPER_BASE_URL=http://localhost:8989
   ```

5. **Interfejs** - instalacja zależności i zbudowanie wersji do uruchomienia z serwerem:
   ```sh
   just frontend-install
   just frontend-build
   ```

6. **Miejsca na mapie** (opcjonalnie, jeśli brak `backend/data/places.json`) — z katalogu `backend/`:
   ```sh
   just extract-places
   ```
   Wymaga `data/raw/hsl.osm.pbf` z kroku 1.

7. **Uruchomienie aplikacji** - z katalogu `backend/`:
   ```sh
   just dev-server
   ```

8. Otwórz w przeglądarce: [http://127.0.0.1:8000/app/](http://127.0.0.1:8000/app/)

   Dokumentacja API (OpenAPI): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Szczegóły kontraktu: [Implementacja](#implementacja).

### Uruchomienie

Po jednorazowej instalacji wystarczy:

1. `just run` - włączenie bazy i GraphHoppera.
2. `cd backend && just dev-server` - serwer z aplikacją.
3. Wejście na `http://127.0.0.1:8000/app/`.

Zatrzymanie usług w Dockerze: `docker compose down`.

### Użytkowanie

Ekran dzieli się na **panel po lewej** (ustawienia wycieczki) i **mapę** (OpenStreetMap).

#### 1. Definicja wycieczki

- **Punkt startowy** - wpisz nazwę i wybierz miejsce z listy (domyślnie: Dworzec Główny, Helsinki).
- **Godzina rozpoczęcia / zakończenia** - w jakich godzinach ma zmieścić się cała wycieczka (np. 09:00-18:00).
- **Dzień wycieczki** - dzień tygodnia, dla którego liczone są godziny otwarcia i optymalizacja trasy (domyślnie: dzisiejszy).

#### 2. Dodawanie atrakcji

- W polu „Dodaj miejsce” wpisz fragment nazwy i wybierz punkt z listy.
- Zobaczysz **godziny otwarcia**; wybrany dzień wycieczki jest wyróżniony.
- Ustaw **czas pobytu** (od-do w godzinach, co pół godziny), np. 1-2 h w muzeum.
- Kliknij **Dodaj do listy**. Miejsca można usuwać z listy „Wybrane miejsca”.

Na mapie widać miejsca do wyboru, punkt startu (zielony znacznik) i wybrane atrakcje. Kliknięcie znacznika pokazuje godziny otwarcia.

#### 3. Wyznaczenie trasy

- Gdy na liście jest co najmniej jedna atrakcja, kliknij **Wyznacz optymalną trasę**.
- Po obliczeniu panel pokazuje **łączny czas wycieczki** i **kolejność odwiedzin**, a na mapie **niebieską linię trasy**.

---

## Założenia

### Obliczanie czasu przejścia pieszo

Do obliczania czasu przejścia pieszego wykorzystujemy silnik **GraphHopper**. Proces wyznaczania trasy opiera się na dedykowanym profilu pieszego oraz uwzględnia parametry dodatkowe, takie jak **heading** (kierunek początkowy). Pozwala on na nakładanie kar na drogi o niepożądanym azymucie, co eliminuje nienaturalne zwroty na starcie i bezpośrednio wpływa na kształt oraz długość trasy. Bazowa prędkość poruszania się dla tego profilu wynosi **5 km/h**. Algorytm stosuje jednak dynamiczne korekty prędkości w zależności od charakterystyki terenu: Jeśli wybrana droga prowadzi przez **schody** lub odcinki oznaczone jako **autostrady** (highway), prędkość dla tych fragmentów jest redukowana do **3 km/h**. Korekta ta pozwala na znacznie dokładniejsze oszacowanie realnego czasu dotarcia do celu.

### Obliczanie czasu przejazdu komunikacją miejską

Model komunikacji miejskiej zaczyna się od wyznaczenia przystanków dostępnych pieszo (znajdujących się w zasięgu określonym przez iloczyn prędkości pieszego i maksymalnego czasu dojścia) zarówno dla punktu startowego, jak i końcowego. Następnie dla tych przystanków wyznaczane są wszystkie możliwe połączenia realizowane wyłącznie transportem publicznym, a z uzyskanych wariantów obliczany jest średni czas przejazdu oraz identyfikowane są pary przystanków (początkowy i końcowy). Na końcu sumowany jest całkowity czas podróży, który obejmuje dojście do przystanku początkowego, przejazd komunikacją miejską oraz dojście od przystanku końcowego do celu, a także wyznaczana jest całkowita długość trasy.

---

## Algorytm

### Dane wejściowe

- $P = \{p_0, p_1, \ldots, p_n\}$ — zbiór atrakcji do odwiedzenia
- $p_0$ — punkt początkowy wycieczki (ustalony, odwiedzony na starcie)
- $[\mathrm{open}_i, \mathrm{close}_i]$ — godziny otwarcia atrakcji $i$
- $[\mathrm{min\_stay}_i, \mathrm{max\_stay}_i]$ — przedział czasu pobytu w atrakcji $i$
- $\mathit{start\_time}$ — czas rozpoczęcia wycieczki
- $\mathit{end\_time}$ — czas zakończenia wycieczki (domyślnie zamknięcie ostatniej odwiedzonej atrakcji)

#### Wstępnie wyliczone dane

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

### Stan

$$
s = (u,\, \mathit{Visited},\, t)
$$

- $u$ — obecna atrakcja (indeks do $P$)
- $\mathit{Visited}$ — zbiór odwiedzonych atrakcji (reprezentacja: bitmask)
- $t$ — aktualny czas (moment wyjścia z atrakcji $u$)

#### Wyliczenia poza stanem

- $\mathit{d\_so\_far}$ — sumaryczny dystans pieszy dotychczasowej trasy
- $\mathit{unused\_so\_far} = \sum_{i \in \mathit{Visited}} (\mathrm{max\_stay}_i - \mathrm{stay}_i)$ — sumaryczny niewykorzystany czas pobytu

Nie wchodzą do klucza stanu $(u, V, t)$.

### Zmienne decyzyjne

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

### Odcinanie

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

### Funkcja kosztu

$$
g(s) = \alpha \cdot \mathit{d\_so\_far} + \beta \cdot \mathit{unused\_so\_far}
$$

gdzie:

- $\mathit{d\_so\_far} = \sum_{(i,j) \in \mathrm{route}} \mathit{walk\_dist}_{ij}$
- $\mathit{unused\_so\_far} = \sum_{i \in \mathit{Visited}} (\mathrm{max\_stay}_i - \mathrm{stay}_i)$

Wagi: $\beta \gg \alpha$ — priorytet leksykograficzny (najpierw maksymalizacja czasu pobytu, potem minimalizacja dystansu).

Wartości domyślne: $\alpha = 1{,}0$ (metr), $\beta = 10000{,}0$ (minuta niewykorzystanego pobytu).

### Funkcja heurystyczna

$$
h(s) = h_{\mathrm{dist}}(s) + h_{\mathrm{stay}}(s)
$$

#### Składnik dystansu

$$
h_{\mathrm{dist}}(s) = \alpha \cdot \mathrm{MST\_weight}(\mathit{Unvisited} \cup \{u\},\, \mathit{walk\_dist})
$$

MST to minimalne drzewo spinające na pozostałych atrakcjach (plus bieżąca) z wagami równymi dystansom pieszym.

#### Składnik czasu pobytu

$$
h_{\mathrm{stay}}(s) = 0
$$

**Eksperymentalne:**

$$
h_{\mathrm{stay}}(s) = \beta \cdot \sum_{i \in \mathit{Unvisited}} \max\bigl(0,\; \mathrm{max\_stay}_i - (\mathrm{close}_i - t^{\min}_{\mathrm{arr},\,i})\bigr)
$$

### Funkcja A*

$$
f(s) = g(s) + h(s)
$$

### Przejście

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

### Wykrycie braku rozwiązania

**Sprawdzenie wstępne (przed A*)**

- Dla każdej atrakcji $i$: sprawdź, czy istnieje jakikolwiek wykonalny czas przyjazdu $t_{\mathrm{arr}} \ge \mathrm{open}_i$ spełniający $t_{\mathrm{arr}} + \mathrm{min\_stay}_i \le \min(\mathrm{close}_i, \mathit{end\_time})$. Jeśli nie — atrakcja $i$ jest indywidualnie niewykonalna.

**Po nieudanym A***

- Pusta kolejka priorytetowa przed osiągnięciem stanu końcowego → problem niewykonalny.

### Optymalizacje funkcji $f(s)$

- Cachowanie MST po masce $\mathit{Unvisited}$
- W każdym kroku potrzebujemy wyliczyć $\mathrm{MST}(\mathit{Unvisited} \cup \{u\})$ w cache mając $\mathrm{MST}(\mathit{Unvisited})$ (własność cięcia MST)
  $$
\mathrm{MST}(S \cup \{u\}) = \mathrm{MST}(S) + \min_{v \in S} \mathit{walk\_dist}_{uv}
$$
- Cachowanie optymalnej ścieżki do stanu $s$: jeśli dwie różne ścieżki prowadzą do identycznego stanu $s = (u, V, t)$, przyszłe opcje z $s$ są identyczne dla obu -> zachowujemy najtańszą. Słownik `best_g`: `dict[state → float]`. Nowy stan dodajemy do kolejki tylko, jeśli $g_{\mathrm{new}} < \texttt{best\_g}[\mathit{state}]$. W przeciwnym razie odrzucamy go.
- Przed dodaniem następnika do kolejki sprawdzamy ograniczenia czasowe. Jeśli $t_{\mathrm{arr}} + \mathrm{min\_stay}_w > \mathrm{close}_w$ lub $> \mathit{end\_time}$, krawędź jest odrzucona przed policzeniem heurystyki.

---

## Implementacja

Tekst uzupełnia [Algorytm](#algorytm) i [Architektura](#architektura): gdzie w kodzie realizowane są główne kroki, bez powtórzenia całej specyfikacji.

### Moduły backendu (`backend/core/`)

| Moduł | Rola |
|-------|------|
| `routing.py` | Czas i dystans pieszo (GraphHopper) oraz trasa z komunikacją miejską (przystanki w bazie, średni czas przejazdu, dojścia pieszo) |
| `trips.py` | Odczyt uśrednionych czasów między parami przystanków z PostGIS |
| `lazy_matrix.py` | Macierz czasów i dystansów między atrakcjami - liczy tylko potrzebne pary |
| `route_optimizer.py` | Optymalizacja kolejności odwiedzin (A*, opis w [Algorytm](#algorytm)) |

Wagi kosztu (`ALPHA`, `BETA`) i wariant pobytu (zachłanny lub co 15 min) są ustawiane w `route_optimizer.py`.

### Macierz przejazdów

Dla każdej pary atrakcji system liczy czas pieszo i czas z KM, a do planowania bierze krótszy wariant. Gdy komunikacja miejska nie ma sensownego połączenia, zostaje sama trasa piesza. Dystans pieszy w koszcie to albo cały odcinek pieszy, albo suma dojść do przystanków - zależnie od wybranego trybu.

### Routing

**Pieszo** - zapytanie do GraphHoppera; powtarzalne wyniki trzymane są w pamięci podręcznej procesu.

**Komunikacja miejska** - w promieniu ok. 10 min pieszo wybierane są przystanki przy obu punktach, z bazy brane są najkorzystniejsze pary ze średnim czasem przejazdu, do tego dochodzą odcinki piesze. Wariant odrzucony jest wtedy, gdy samo dojście do przystanku trwa dłużej niż przejście bezpośrednie.

### Optymalizator wycieczki

Przepływ zgodny z [Algorytmem](#algorytm):

1. Zbudowanie macierzy przejazdów między atrakcjami.
2. Sprawdzenie, czy każda atrakcja da się odwiedzić w swoim oknie czasowym.
3. Przeszukiwanie A* - stan to ostatnia atrakcja, zbiór odwiedzonych (maska bitowa) i czas wyjścia.
4. Dla każdego kandydata: dojazd, ewentualne czekanie na otwarcie, wybór czasu pobytu, aktualizacja kosztu (dystans pieszy + niewykorzystany czas pobytu).
5. Heurystyka oparta na minimalnym drzewie spinającym pozostałe atrakcje; powtarzające się podproblemy są pomijane, jeśli już znaleziono tańszy stan.

Sukces: wszystkie atrakcje odwiedzone w kolejności zwróconej przez API. Brak rozwiązania: komunikat błędu dla użytkownika (patrz sekcja API).

### API HTTP

Schematy Pydantic i interaktywna dokumentacja: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Swagger FastAPI, gdy działa `just dev-server`).

#### GET `/places`

Zwraca listę atrakcji z `backend/data/places.json` (generowana skryptem `just extract-places` w katalogu `backend/`).

Przykładowy element:

```json
{
  "id": 0,
  "name": "Helsinki Central Park",
  "lat": 60.237373,
  "lng": 24.920478,
  "hours": [
    { "day": 1, "label": "Monday", "time": "Open 24 hours" }
  ]
}
```

| Status | Odpowiedź |
|--------|-----------|
| 200 | tablica miejsc |
| 503 | brak `places.json` — uruchom `just extract-places` |

#### POST `/trip/optimize`

Optymalizacja kolejności odwiedzin. **Wszystkie czasy w minutach od północy** (np. 540 = 09:00). Współrzędne: `lat`, `lon`.

**Walidacja wejścia** (FastAPI/Pydantic): HTTP 422, `detail` jako lista pól — np. brak wymaganego pola, zły typ.

### Jednostki i wydajność

W solverze czas jest w minutach od północy; GraphHopper zwraca sekundy - konwersja odbywa się przy budowie macierzy.

Szczegółowe pomiary wariantów algorytmu: [Eksperymenty](#eksperymenty).

---

## Eksperymenty

Wygenerowano automatycznie z plików `experiments/outputs/results.csv` oraz `experiments/outputs/aggregated.csv`.

### Konfiguracja

#### Wymagania wstępne

- Środowisko Pythona zsynchronizowane w `experiments/` (`just sync`).
- Dla pomiarów na danych rzeczywistych (tryb `real`): uruchomiony i załadowany GraphHopper oraz PostGIS.

#### Polecenia uruchomienia

- Główny zestaw na danych syntetycznych: `uv run python -m experiments.app suite=synthetic_main setup=baseline`
- Wpływ heurystyki (wariant z heurystyką i bez): `uv run python -m experiments.app suite=heuristic_ablation setup=baseline`
- Punkt odniesienia brute-force: `uv run python -m experiments.app suite=bf_reference_small_n setup=window_stress`
- Walidacja ręcznie dobranych scenariuszy: `uv run python -m experiments.app suite=handpicked_validation setup=infeasible_sanity`
- Punkt odniesienia na danych z Helsinek: `uv run python -m experiments.app suite=real_reference setup=real_reference matrix.mode=real infra.database_url=... infra.graphhopper_base_url=...`

### Jak czytać wykresy

- Każdy wykres skalowania ma panel profilu **relaxed** (luźne okno wycieczki) i **tight** (ciasne). Przy ciasnym oknie przeszukiwanie szybciej się kończy, więc wartości bezwzględne są znacznie mniejsze niż przy luźnym.
- Osie Y na wykresach skalowania są **logarytmiczne**. Spadek lub płaski odcinek blisko prawego brzegu krzywej zwykle oznacza, że algorytm trafił w limit czasu na trudniejszych scenariuszach (patrz adnotacja `ok/total`).
- **Pusty marker** z `k/n` obok oznacza, że tylko `k` z `n` przebiegów przy danym `n_attractions` zakończyło się w limicie czasu. Mediana na wykresie odzwierciedla więc tylko łatwiejsze przypadki i należy ją traktować jako dolne oszacowanie.
- Konkretnie: `bruteforce_intervals` ma szczyt około `n=9` (relaxed) i wygląda na *spadek* przy `n=10` wyłącznie dlatego, że 11 z 12 scenariuszy przekroczyło limit czasu przy `n=10` i przetrwał tylko najtańszy.

### Praktyczne wnioski

- A* z rozgałęzianiem po przedziałach pobytu dorównuje zachłannemu A* pod względem jakości i pozostaje wyraźnie poniżej jednej sekundy do `n_attractions = 12` na danych syntetycznych (patrz skalowanie czasu). Przy `n=15` profil relaxed staje się trudniejszy i w limicie czasu kończy się tylko profil tight.
- Pełne przeszukiwanie (brute-force) jako punkt odniesienia potwierdza, że A* jest optymalny w każdym rozwiązywalnym przypadku (patrz tabela luki optymalności poniżej: maksymalna luka to w praktyce szum zmiennoprzecinkowy).
- Pomiary na mapie i rozkładach HSL są zdominowane przez zapytania do GraphHoppera i PostGIS: czas wykonania jest rzędu około dwóch wielkości większy niż na danych syntetycznych przy tym samym `n_attractions`, podczas gdy samo przeszukiwanie rozwija tyle samo węzłów (patrz wykres real vs fixture).

### Główne tabele

#### Status według trybu i eksperymentu

| mode | experiment | runs | ok | ok_rate |
| --- | --- | --- | --- | --- |
| fixture | astar_greedy | 220 | 205 | 0.932 |
| fixture | astar_intervals | 292 | 277 | 0.949 |
| fixture | astar_intervals_no_heuristic | 76 | 72 | 0.947 |
| fixture | bruteforce_greedy | 124 | 121 | 0.976 |
| fixture | bruteforce_intervals | 124 | 110 | 0.887 |
| real | astar_greedy | 9 | 9 | 1.0 |
| real | astar_intervals | 9 | 9 | 1.0 |

#### Podsumowanie czasu i jakości

| mode | experiment | avg_ok_rate | avg_wall_time_ms | avg_expanded_nodes | avg_peak_memory_mb | median_objective_cost | avg_stay_utilization |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fixture | astar_greedy | 0.818 | 67.104 | 646.458 | 0.252 | 14913.794 | 1.0 |
| fixture | astar_intervals | 0.857 | 62.359 | 546.83 | 0.32 | 14913.794 | 1.0 |
| fixture | astar_intervals_no_heuristic | 0.692 | 1565.114 | 11709.844 | 74.998 | 14250.845 | 1.0 |
| fixture | bruteforce_greedy | 0.786 | 418.142 | 23144.75 | 4.101 | 13877.614 | 1.0 |
| fixture | bruteforce_intervals | 0.72 | 2561.584 | 141217.864 | 23.853 | 15270.08 | 1.0 |
| real | astar_greedy | 1.0 | 2755.717 | 533.0 | 3.612 | 2875.748 | 1.0 |
| real | astar_intervals | 1.0 | 2819.131 | 533.0 | 8.479 | 2875.748 | 1.0 |

#### Luka optymalności względem brute-force (na algorytm / profil)

| experiment | profile | compared_cases | max_abs_gap | median_abs_gap |
| --- | --- | --- | --- | --- |
| astar_greedy | relaxed | 60 | 4.90e-03 | 0.00e+00 |
| astar_greedy | tight | 60 | 0.00e+00 | 0.00e+00 |
| astar_intervals | relaxed | 49 | 4.90e-03 | 0.00e+00 |
| astar_intervals | tight | 60 | 0.00e+00 | 0.00e+00 |

#### Podsumowanie przyspieszenia heurystyki

| mode | mean_speedup_vs_no_heuristic | sample_count |
| --- | --- | --- |
| fixture | 85.143 | 144 |

#### Podsumowanie poprawności wykonalności (ręcznie dobrane scenariusze brzegowe)

| mode | checked_cases | correct_cases | correct_rate |
| --- | --- | --- | --- |
| fixture | 17 | 16 | 0.941 |

### Wykresy końcowe

#### Skalowanie czasu (dane syntetyczne)

![Skalowanie czasu (dane syntetyczne)](../figures/experiments/runtime_scaling.png)

#### Skalowanie pamięci (dane syntetyczne)

![Skalowanie pamięci (dane syntetyczne)](../figures/experiments/memory_scaling.png)

#### Czas: Helsinki vs dane syntetyczne

![Czas Helsinki vs dane syntetyczne](../figures/experiments/real_vs_fixture.png)

#### Pamięć: Helsinki vs dane syntetyczne

![Pamięć Helsinki vs dane syntetyczne](../figures/experiments/real_vs_fixture_memory.png)

### Dodatek: wewnętrzne metryki przeszukiwania

Te wykresy opisują wewnętrzne działanie algorytmu (wysiłek przeszukiwania, porównanie z wariantem bez heurystyki), a nie czas widziany od strony aplikacji. Zostawione dla kompletności.

#### Skalowanie rozwiniętych węzłów (dane syntetyczne)

![Skalowanie rozwiniętych węzłów (dane syntetyczne)](../figures/experiments/expanded_nodes_scaling.png)

#### Wpływ heurystyki na czas (dane syntetyczne)

![Wpływ heurystyki na czas (dane syntetyczne)](../figures/experiments/heuristic_ablation.png)
