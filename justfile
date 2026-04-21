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


# === SETUP ===

_init: 
    echo "Initializing project..."
    mkdir -p data
    mkdir -p data/containers

setup: (_init) (download-data) (prepare-data) 
    echo "Project initialized successfully"