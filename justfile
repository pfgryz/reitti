# === DATA PREPARATION ===

download-osm:
    echo "Downloading OSM data..."
    mkdir -p data/raw
    wget -O data/raw/hsl.osm.pbf https://karttapalvelu.storage.hsldev.com/hsl.osm/hsl.osm.pbf

download-gtfs:
    echo "Downloading GTFS data..."
    mkdir -p data/raw
    wget -O data/raw/hsl.zip  https://infopalvelut.storage.hsldev.com/gtfs/hsl.zip

download-data: (download-osm) (download-gtfs)
    echo "Data downloaded successfully"

prepare-gtfs:
    echo "Preparing GTFS data..."
    mkdir -p data/gtfs
    unzip data/raw/hsl.zip -d data/gtfs
    echo "GTFS data prepared successfully"

prepare-data: (prepare-gtfs)


# == CONTAINERS ==

prepare-graphhopper:
    echo "Preparing GraphHopper data..."
    mkdir -p data/containers/graphhopper
    cp data/raw/hsl.osm.pbf data/containers/graphhopper/hsl.osm.pbf
    cp resources/graphhopper-config.yaml data/containers/graphhopper-config.yaml
    echo "GraphHopper data prepared successfully"

prepare-postgis:
    echo "Preparing PostGIS data..."
    docker compose exec -T db psql -U admin -d Reitti -f /dev/stdin < backend/db/migrations/0_init_db.sql
    docker compose exec -T db psql -U admin -d Reitti -f /dev/stdin < backend/db/migrations/1_load_data.sql
    docker compose exec -T db psql -U admin -d Reitti -f /dev/stdin < backend/db/migrations/2_init_geom.sql
    docker compose exec -T db psql -U admin -d Reitti -f /dev/stdin < backend/db/migrations/3_stop_times_indexes.sql
    docker compose exec -T db psql -U admin -d Reitti -f /dev/stdin < backend/db/migrations/4_stop_pair_avg_time.sql
    echo "PostGIS data prepared successfully"

# === SETUP ===

_init: 
    echo "Initializing project..."
    mkdir -p data
    mkdir -p data/containers

setup: (_init) (download-data) (prepare-data) (prepare-graphhopper)
    echo "Project initialized successfully"

run:
    docker compose up -d

# === FRONTEND ===

frontend-install:
    just --working-directory frontend install

frontend-build:
    just --working-directory frontend build
