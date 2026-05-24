# Implementacja

Tekst uzupełnia [[algorytm]] i [[architektura]]: gdzie w kodzie realizowane są główne kroki, bez powtórzenia całej specyfikacji.

## Moduły backendu (`backend/core/`)

| Moduł | Rola |
|-------|------|
| `routing.py` | Czas i dystans pieszo (GraphHopper) oraz trasa z komunikacją miejską (przystanki w bazie, średni czas przejazdu, dojścia pieszo) |
| `trips.py` | Odczyt uśrednionych czasów między parami przystanków z PostGIS |
| `lazy_matrix.py` | Macierz czasów i dystansów między atrakcjami - liczy tylko potrzebne pary |
| `route_optimizer.py` | Optymalizacja kolejności odwiedzin (A*, opis w [[algorytm]]) |

Wagi kosztu (`ALPHA`, `BETA`) i wariant pobytu (zachłanny lub co 15 min) są ustawiane w `route_optimizer.py`.

## Macierz przejazdów

Dla każdej pary atrakcji system liczy czas pieszo i czas z KM, a do planowania bierze krótszy wariant. Gdy komunikacja miejska nie ma sensownego połączenia, zostaje sama trasa piesza. Dystans pieszy w koszcie to albo cały odcinek pieszy, albo suma dojść do przystanków - zależnie od wybranego trybu.

## Routing

**Pieszo** - zapytanie do GraphHoppera; powtarzalne wyniki trzymane są w pamięci podręcznej procesu.

**Komunikacja miejska** - w promieniu ok. 10 min pieszo wybierane są przystanki przy obu punktach, z bazy brane są najkorzystniejsze pary ze średnim czasem przejazdu, do tego dochodzą odcinki piesze. Wariant odrzucony jest wtedy, gdy samo dojście do przystanku trwa dłużej niż przejście bezpośrednie.

## Optymalizator wycieczki

Przepływ zgodny z [[algorytm]]:

1. Zbudowanie macierzy przejazdów między atrakcjami.
2. Sprawdzenie, czy każda atrakcja da się odwiedzić w swoim oknie czasowym.
3. Przeszukiwanie A* - stan to ostatnia atrakcja, zbiór odwiedzonych (maska bitowa) i czas wyjścia.
4. Dla każdego kandydata: dojazd, ewentualne czekanie na otwarcie, wybór czasu pobytu, aktualizacja kosztu (dystans pieszy + niewykorzystany czas pobytu).
5. Heurystyka oparta na minimalnym drzewie spinającym pozostałe atrakcje; powtarzające się podproblemy są pomijane, jeśli już znaleziono tańszy stan.

Sukces: wszystkie atrakcje odwiedzone w kolejności zwróconej przez API. Brak rozwiązania: komunikat błędu dla użytkownika.

Backend udostępnia wynik optymalizacji przez API; frontend wysyła listę atrakcji i godziny, a w odpowiedzi dostaje kolejność wizyt, czasy i dane do narysowania trasy na mapie.

## Jednostki i wydajność

W solverze czas jest w minutach od północy; GraphHopper zwraca sekundy - konwersja odbywa się przy budowie macierzy.

Szczegółowe pomiary wariantów algorytmu: `docs/experiments.md`.
