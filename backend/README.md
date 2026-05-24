# Reitti Backend

## Development
To run the development server, use the following command:
```sh
uv run fastapi dev main.py
```
or the shorthand:
```sh
just dev-server
```

## Places (attractions)

Attractions are stored in `data/places.json`. Regenerate from local `data/raw/hsl.osm.pbf` (same file GraphHopper uses — no Overpass):

```sh
just extract-places          # default: 50 POIs
just extract-places count=80
# or: uv run --group scripts python scripts/extract_places.py -n 80
```

Requires `hsl.osm.pbf` from `just download-osm` in project root. Picks important POIs (scored by OSM tags) spread across the map grid, plus Helsinki Central Station. Names and `opening_hours` come from OSM; missing or unparsed hours default to open 24 hours.

## Production
To run the production server, use the following command:
```sh
uv run fastapi run main.py
```
or the shorthand:
```sh
just server
```