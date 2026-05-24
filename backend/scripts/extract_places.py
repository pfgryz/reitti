#!/usr/bin/env python3
import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import osmium
from tqdm import tqdm

OUT = Path(__file__).resolve().parent.parent / "data" / "places.json"
DEFAULT_PBF = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "hsl.osm.pbf"
BBOX = (60.13, 24.90, 60.30, 25.06)
DEFAULT_COUNT = 50
GRID_ROWS, GRID_COLS = 7, 8

HARDCODED_STATION = {
    "name": "Helsinki Central Station",
    "lat": 60.171852,
    "lng": 24.941409,
}

DAYS = [
    (1, "Monday"), (2, "Tuesday"), (3, "Wednesday"), (4, "Thursday"),
    (5, "Friday"), (6, "Saturday"), (0, "Sunday"),
]
DAY_ORDER = [1, 2, 3, 4, 5, 6, 0]
DAY_CODES = {"mo": 1, "tu": 2, "we": 3, "th": 4, "fr": 5, "sa": 6, "su": 0}
MONTH_CODES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
SEASON_PREFIX = re.compile(r"^[A-Za-z]{3}-[A-Za-z]{3}:\s*")

TOURISM_GOOD = {"museum", "attraction", "gallery", "theme_park", "zoo", "aquarium", "viewpoint"}
TOURISM_SKIP = {"information", "artwork", "board", "camp_site", "yes", "picnic_site"}
HISTORIC_GOOD = {
    "castle", "cathedral", "church", "fortress", "monument", "building",
    "ruins", "archaeological_site", "manor", "city_gate",
}
HISTORIC_SKIP = {"memorial", "memorial_plaque", "boundary_stone", "stone", "tomb", "wayside_cross"}


@dataclass
class Candidate:
    name: str
    tags: dict
    lat: float
    lon: float
    score: int


def in_bbox(lat: float, lon: float) -> bool:
    s, w, n, e = BBOX
    return s <= lat <= n and w <= lon <= e


def tags_of(obj) -> dict:
    return {t.k: t.v for t in obj.tags}


def pick_name(tags: dict) -> str:
    return tags.get("name:en") or tags.get("name") or tags.get("name:fi") or ""


def poi_score(tags: dict) -> int:
    name = pick_name(tags)
    if not name:
        return 0

    score = 0
    tourism = tags.get("tourism")
    if tourism:
        if tourism in TOURISM_SKIP:
            return 0
        score += 30 if tourism in TOURISM_GOOD else 12

    historic = tags.get("historic")
    if historic:
        if historic in HISTORIC_SKIP:
            return 0
        score += 28 if historic in HISTORIC_GOOD else 10

    amenity = tags.get("amenity")
    if amenity in ("theatre", "arts_centre", "planetarium"):
        score += 22

    if tags.get("railway") == "station":
        score += 18

    if tags.get("leisure") == "park":
        score += 14 if tags.get("wikidata") else 6

    if tags.get("wikidata"):
        score += 15
    if tags.get("wikipedia"):
        score += 8

    return score


def open24h_hours() -> list[dict]:
    return [{"day": d, "label": label, "time": "Open 24 hours"} for d, label in DAYS]


def expand_days(spec: str) -> list[int]:
    spec = spec.strip().lower()
    if "-" not in spec:
        return [DAY_CODES[spec]] if spec in DAY_CODES else []
    start, end = spec.split("-", 1)
    if start not in DAY_CODES or end not in DAY_CODES:
        return []
    order = DAY_ORDER
    i, j = order.index(DAY_CODES[start]), order.index(DAY_CODES[end])
    if i <= j:
        return order[i : j + 1]
    return order[i:] + order[: j + 1]


def month_in_season(month: int, start: int, end: int) -> bool:
    if start <= end:
        return start <= month <= end
    return month >= start or month <= end


def season_active(rule: str, month: int) -> bool:
    m = re.match(r"^([A-Za-z]{3})-([A-Za-z]{3}):", rule.strip())
    if not m:
        return True
    a, b = m.group(1).lower(), m.group(2).lower()
    if a not in MONTH_CODES or b not in MONTH_CODES:
        return True
    return month_in_season(month, MONTH_CODES[a], MONTH_CODES[b])


def strip_season(rule: str) -> str:
    return SEASON_PREFIX.sub("", rule.strip())


def apply_time_rule(slots: dict[int, str], rule: str) -> bool:
    rule = strip_season(rule)
    if re.fullmatch(r"[A-Za-z\-]+\s+closed", rule, re.I):
        for d in expand_days(rule.split()[0]):
            slots[d] = "Closed"
        return True
    m = re.match(
        r"(?:(?P<days>[A-Za-z\-]+)\s+)?(?P<open>\d{1,2}:\d{2})\s*-\s*(?P<close>\d{1,2}:\d{2})",
        rule,
        re.I,
    )
    if not m:
        return False
    text = f"{m.group('open')} - {m.group('close')}"
    days = expand_days(m.group("days")) if m.group("days") else DAY_ORDER
    if not days:
        return False
    for d in days:
        slots[d] = text
    return True


def parse_opening_hours(raw: str, month: int | None = None) -> list[dict] | None:
    raw = raw.strip()
    if not raw:
        return None
    if re.search(r"24\s*/\s*7", raw, re.I):
        return open24h_hours()

    month = month or date.today().month
    slots = {d: "Closed" for d, _ in DAYS}
    applied = False

    for rule in raw.split(";"):
        rule = rule.strip()
        if not rule or not season_active(rule, month):
            continue
        if not apply_time_rule(slots, rule):
            return None
        applied = True

    if not applied:
        for rule in raw.split(";"):
            rule = rule.strip()
            if not rule:
                continue
            if apply_time_rule(slots, strip_season(rule)):
                applied = True
        if not applied:
            return None

    return [{"day": d, "label": label, "time": slots[d]} for d, label in DAYS]


def resolve_hours(tags: dict) -> list[dict]:
    raw = tags.get("opening_hours")
    if not raw:
        return open24h_hours()
    parsed = parse_opening_hours(raw)
    if parsed:
        return parsed
    print(f"unparsed hours for {pick_name(tags)}: {raw}", file=sys.stderr)
    return open24h_hours()


def load_candidates(pbf: Path) -> list[Candidate]:
    node_pos: dict[int, tuple[float, float]] = {}
    pbf_path = str(pbf)

    with tqdm(desc="Pass 1: index nodes", unit=" nodes", dynamic_ncols=True) as bar:
        class Pass1(osmium.SimpleHandler):
            def node(self, n):
                bar.update(1)
                if n.location.valid():
                    node_pos[n.id] = (n.location.lat, n.location.lon)

        Pass1().apply_file(pbf_path)

    raw: list[Candidate] = []

    with tqdm(desc="Pass 2: scan POI", unit=" objs", dynamic_ncols=True) as bar:
        class Pass2(osmium.SimpleHandler):
            def node(self, n):
                bar.update(1)
                if not n.location.valid():
                    return
                tags = tags_of(n)
                score = poi_score(tags)
                if score <= 0:
                    return
                lat, lon = n.location.lat, n.location.lon
                if in_bbox(lat, lon):
                    raw.append(Candidate(pick_name(tags), tags, lat, lon, score))

            def way(self, w):
                bar.update(1)
                tags = tags_of(w)
                score = poi_score(tags)
                if score <= 0:
                    return
                locs = [node_pos[r.ref] for r in w.nodes if r.ref in node_pos]
                if not locs:
                    return
                lat = sum(p[0] for p in locs) / len(locs)
                lon = sum(p[1] for p in locs) / len(locs)
                if in_bbox(lat, lon):
                    raw.append(Candidate(pick_name(tags), tags, lat, lon, score))

        Pass2().apply_file(pbf_path)

    return raw


def dedupe(candidates: list[Candidate]) -> list[Candidate]:
    best: dict[tuple[int, int], Candidate] = {}
    for c in candidates:
        key = (round(c.lat, 3), round(c.lon, 3))
        if key not in best or c.score > best[key].score:
            best[key] = c
    return list(best.values())


def select_spread(candidates: list[Candidate], count: int) -> list[Candidate]:
    s, w, n, e = BBOX
    chosen: list[Candidate] = []
    used: set[tuple[int, int]] = set()

    for ri in range(GRID_ROWS):
        for ci in range(GRID_COLS):
            if len(chosen) >= count:
                break
            lat_lo = s + (n - s) * ri / GRID_ROWS
            lat_hi = s + (n - s) * (ri + 1) / GRID_ROWS
            lon_lo = w + (e - w) * ci / GRID_COLS
            lon_hi = w + (e - w) * (ci + 1) / GRID_COLS
            in_cell = [
                c for c in candidates
                if (round(c.lat, 3), round(c.lon, 3)) not in used
                and lat_lo <= c.lat < lat_hi
                and lon_lo <= c.lon < lon_hi
            ]
            if not in_cell:
                continue
            pick = max(in_cell, key=lambda c: c.score)
            chosen.append(pick)
            used.add((round(pick.lat, 3), round(pick.lon, 3)))

    rest = sorted(
        [c for c in candidates if (round(c.lat, 3), round(c.lon, 3)) not in used],
        key=lambda c: c.score,
        reverse=True,
    )
    for c in rest:
        if len(chosen) >= count:
            break
        chosen.append(c)
        used.add((round(c.lat, 3), round(c.lon, 3)))

    return chosen[:count]


def near_station(lat: float, lon: float) -> bool:
    return (
        abs(lat - HARDCODED_STATION["lat"]) < 0.002
        and abs(lon - HARDCODED_STATION["lng"]) < 0.002
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract POIs from OSM PBF into places.json")
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=f"how many POIs to pick from the map (default: {DEFAULT_COUNT})",
    )
    parser.add_argument(
        "pbf",
        nargs="?",
        default=str(DEFAULT_PBF),
        help="path to .osm.pbf (default: data/raw/hsl.osm.pbf)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count < 1:
        print("count must be >= 1", file=sys.stderr)
        return 1

    pbf = Path(args.pbf)
    if not pbf.is_file():
        print(f"missing file: {pbf}", file=sys.stderr)
        print("run: just download-osm (from project root)", file=sys.stderr)
        return 1

    all_pois = dedupe(load_candidates(pbf))
    selected = select_spread(all_pois, max(0, args.count - 1))

    result = [
        {
            "id": 0,
            "name": HARDCODED_STATION["name"],
            "lat": HARDCODED_STATION["lat"],
            "lng": HARDCODED_STATION["lng"],
            "hours": open24h_hours(),
        }
    ]
    for c in tqdm(selected, desc="Build JSON", unit=" places", dynamic_ncols=True):
        if near_station(c.lat, c.lon):
            continue
        raw_hours = c.tags.get("opening_hours")
        entry = {
            "id": len(result),
            "name": c.name,
            "lat": round(c.lat, 6),
            "lng": round(c.lon, 6),
            "hours": resolve_hours(c.tags),
        }
        if raw_hours:
            entry["opening_hours"] = raw_hours
        result.append(entry)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(result)} places from {pbf} -> {OUT}")
    return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(main())
