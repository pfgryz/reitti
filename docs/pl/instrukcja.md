# Instrukcja

## Wymagania

- [Docker](https://docs.docker.com/get-docker/)
- [just](https://github.com/casey/just)
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+

Pierwsze `just setup` pobiera mapę OSM i rozkłady jazdy HSL - pliki są duże; potrzebne jest połączenie z internetem i kilka gigabajtów wolnego miejsca.

## Instalacja

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

   Dokumentacja API (OpenAPI): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Szczegóły kontraktu: [[implementacja]].

## Uruchomienie

Po jednorazowej instalacji wystarczy:

1. `just run` - włączenie bazy i GraphHoppera.
2. `cd backend && just dev-server` - serwer z aplikacją.
3. Wejście na `http://127.0.0.1:8000/app/`.

Zatrzymanie usług w Dockerze: `docker compose down`.

## Użytkowanie

Ekran dzieli się na **panel po lewej** (ustawienia wycieczki) i **mapę** (OpenStreetMap).

### 1. Definicja wycieczki

- **Punkt startowy** - wpisz nazwę i wybierz miejsce z listy (domyślnie: Dworzec Główny, Helsinki).
- **Godzina rozpoczęcia / zakończenia** - w jakich godzinach ma zmieścić się cała wycieczka (np. 09:00-18:00).
- **Dzień wycieczki** - dzień tygodnia, dla którego liczone są godziny otwarcia i optymalizacja trasy (domyślnie: dzisiejszy).

### 2. Dodawanie atrakcji

- W polu „Dodaj miejsce” wpisz fragment nazwy i wybierz punkt z listy.
- Zobaczysz **godziny otwarcia**; wybrany dzień wycieczki jest wyróżniony.
- Ustaw **czas pobytu** (od-do w godzinach, co pół godziny), np. 1-2 h w muzeum.
- Kliknij **Dodaj do listy**. Miejsca można usuwać z listy „Wybrane miejsca”.

Na mapie widać miejsca do wyboru, punkt startu (zielony znacznik) i wybrane atrakcje. Kliknięcie znacznika pokazuje godziny otwarcia.

### 3. Wyznaczenie trasy

- Gdy na liście jest co najmniej jedna atrakcja, kliknij **Wyznacz optymalną trasę**.
- Po obliczeniu panel pokazuje **łączny czas wycieczki** i **kolejność odwiedzin**, a na mapie **niebieską linię trasy**.