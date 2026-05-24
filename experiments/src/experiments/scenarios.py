from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from omegaconf import OmegaConf
from pydantic import BaseModel, ConfigDict, StrictInt, ValidationError, model_validator

from . import ensure_backend_path
from .matrices import FixtureMatrixConfig, precompute_fixture_edges

ensure_backend_path()

from core import Point  # noqa: E402
from core.route_optimizer import (  # noqa: E402
    Attraction,
    AttractionType,
    OpeningHours,
    RouteOptimizationInput,
    StayBounds,
)

CONF_ROOT = Path(__file__).resolve().parents[2] / "conf"
TOUR_ATTEMPTS = 50
TIGHT_WINDOW_SLACK = 5.0
IMPOSSIBLE_WINDOW_OFFSET = 60.0
IMPOSSIBLE_WINDOW_LENGTH = 10.0
IMPOSSIBLE_MIN_STAY = 30.0


class ExplicitAttractionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    open: StrictInt
    close: StrictInt
    min_stay: StrictInt
    max_stay: StrictInt

    @model_validator(mode="after")
    def _validate_ranges(self) -> ExplicitAttractionRow:
        if self.open >= self.close:
            raise ValueError("explicit attraction open must be < close")
        if self.min_stay > self.max_stay:
            raise ValueError("explicit attraction min_stay must be <= max_stay")
        return self


class HandpickedCaseRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    profile: Literal["relaxed", "tight", "impossible"]
    seed: StrictInt
    case_mode: Literal["generated", "explicit"] = "generated"
    n_attractions: StrictInt | None = None
    attractions: list[ExplicitAttractionRow] | None = None
    start_time: StrictInt | None = None
    end_time: StrictInt | None = None

    @model_validator(mode="after")
    def _validate_mode_fields(self) -> HandpickedCaseRow:
        self.id = self.id.strip()
        if not self.id:
            raise ValueError("handpicked case id must be a non-empty string")
        if self.case_mode == "generated":
            if self.n_attractions is None or self.n_attractions < 1:
                raise ValueError("handpicked case n_attractions must be an int >= 1")
            return self
        if self.attractions is None:
            raise ValueError("explicit case attractions must be provided as a list")
        return self


@dataclass(frozen=True, slots=True)
class SetupConfig:
    name: str
    start_time: int
    end_time: int
    min_stay: int
    extra_max: int
    base_lat: float
    base_lon: float
    location_spread: float


@dataclass(frozen=True, slots=True)
class SuiteConfig:
    name: str
    variants: tuple[str, ...]
    matrix_mode: str
    n_attractions: tuple[int, ...]
    seed_count: int
    profiles: tuple[str, ...]
    include_handpicked: bool = False
    handpicked_file: str = "handpicked/boundary.yaml"


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    seed: int
    n_attractions: int
    profile: str
    suite: str
    setup_name: str
    problem: RouteOptimizationInput


def _attraction(
    *,
    lat: float,
    lon: float,
    open_at: float,
    close_at: float,
    min_stay: float,
    max_stay: float,
) -> Attraction:
    return Attraction(
        position=Point(lat=lat, lon=lon),
        opening_hours=OpeningHours(open=open_at, close=close_at),
        stay=StayBounds(min=min_stay, max=max_stay),
        type=AttractionType.OTHER,
    )


def _origin(setup: SetupConfig) -> Attraction:
    return _attraction(
        lat=setup.base_lat,
        lon=setup.base_lon,
        open_at=0.0,
        close_at=24 * 60,
        min_stay=0.0,
        max_stay=0.0,
    )


def _random_position(setup: SetupConfig, rng: random.Random) -> tuple[float, float]:
    return (
        setup.base_lat + rng.uniform(-setup.location_spread, setup.location_spread),
        setup.base_lon + rng.uniform(-setup.location_spread, setup.location_spread),
    )


def _sample_walkable_tour(
    *,
    n: int,
    times: list[list[float | None]],
    setup: SetupConfig,
    rng: random.Random,
) -> tuple[list[int], list[float]]:
    """Random-greedy walk from node 0 with restart-on-dead-end retries.

    Each attempt extends the tour by picking uniformly at random from the unvisited
    nodes that are reachable from the current node and whose minimum stay fits
    before end_time. Stay time is fixed to setup.min_stay so the tour is the
    shortest legal one; profile-dependent slack is added later as window padding
    or as max_stay. Sparse matrices may need several restarts because greedy has
    no backtracking; the consumed RNG state guarantees that successive attempts
    explore different choices.
    """
    for _ in range(TOUR_ATTEMPTS):
        result = _attempt_walk(n=n, times=times, setup=setup, rng=rng)
        if result is not None:
            return result
    raise RuntimeError(
        f"cannot construct a feasible tour for n={n} setup={setup.name} after "
        f"{TOUR_ATTEMPTS} attempts; widen [start_time, end_time] or matrix density"
    )


def _attempt_walk(
    *,
    n: int,
    times: list[list[float | None]],
    setup: SetupConfig,
    rng: random.Random,
) -> tuple[list[int], list[float]] | None:
    remaining = set(range(1, n))
    order: list[int] = []
    arrivals: list[float] = []
    current = 0
    now = float(setup.start_time)
    while remaining:
        candidates: list[tuple[int, float]] = []
        for idx in remaining:
            travel = times[current][idx]
            if travel is None:
                continue
            arrival = now + travel
            if arrival + setup.min_stay > setup.end_time:
                continue
            candidates.append((idx, arrival))
        if not candidates:
            return None
        idx, arrival = rng.choice(candidates)
        order.append(idx)
        arrivals.append(arrival)
        remaining.remove(idx)
        current = idx
        now = arrival + setup.min_stay
    return order, arrivals


def _generated_problem(
    *,
    n: int,
    profile: str,
    seed: int,
    setup: SetupConfig,
    fixture_cfg: FixtureMatrixConfig,
) -> RouteOptimizationInput:
    if profile == "impossible":
        return _impossible_problem(n=n, setup=setup, seed=seed)
    rng = random.Random(seed)
    attractions: list[Attraction] = [_origin(setup)]
    if n > 1:
        times, _ = precompute_fixture_edges(n, fixture_cfg, seed=seed)
        order, arrivals = _sample_walkable_tour(
            n=n, times=times, setup=setup, rng=rng
        )
        arrival_by_index = dict(zip(order, arrivals, strict=True))
        stay = float(setup.min_stay)
        for idx in range(1, n):
            arrival = arrival_by_index[idx]
            finish = arrival + stay
            if profile == "tight":
                open_at = max(float(setup.start_time), arrival - TIGHT_WINDOW_SLACK)
                close_at = min(float(setup.end_time), finish + TIGHT_WINDOW_SLACK)
                min_stay = stay
                max_stay = stay
            else:  # relaxed
                open_at = float(setup.start_time)
                close_at = float(setup.end_time)
                min_stay = stay
                max_stay = stay + float(setup.extra_max)
            lat, lon = _random_position(setup, rng)
            attractions.append(
                _attraction(
                    lat=lat,
                    lon=lon,
                    open_at=open_at,
                    close_at=close_at,
                    min_stay=min_stay,
                    max_stay=max_stay,
                )
            )
    return RouteOptimizationInput(
        start_time=float(setup.start_time),
        attractions=attractions,
        end_time=float(setup.end_time),
    )


def _impossible_problem(
    *, n: int, setup: SetupConfig, seed: int
) -> RouteOptimizationInput:
    rng = random.Random(seed)
    end = float(setup.end_time)
    open_at = end - IMPOSSIBLE_WINDOW_OFFSET
    close_at = open_at + IMPOSSIBLE_WINDOW_LENGTH
    attractions: list[Attraction] = [_origin(setup)]
    for _ in range(1, n):
        lat, lon = _random_position(setup, rng)
        attractions.append(
            _attraction(
                lat=lat,
                lon=lon,
                open_at=open_at,
                close_at=close_at,
                min_stay=IMPOSSIBLE_MIN_STAY,
                max_stay=IMPOSSIBLE_MIN_STAY,
            )
        )
    return RouteOptimizationInput(
        start_time=float(setup.start_time),
        attractions=attractions,
        end_time=end,
    )


def _explicit_problem(
    *,
    setup: SetupConfig,
    seed: int,
    start_time: int,
    end_time: int,
    attractions_data: list[dict[str, Any]],
) -> RouteOptimizationInput:
    rng = random.Random(seed)
    attractions: list[Attraction] = [_origin(setup)]
    for row in attractions_data:
        lat, lon = _random_position(setup, rng)
        attractions.append(
            _attraction(
                lat=lat,
                lon=lon,
                open_at=float(row["open"]),
                close_at=float(row["close"]),
                min_stay=float(row["min_stay"]),
                max_stay=float(row["max_stay"]),
            )
        )
    return RouteOptimizationInput(
        start_time=float(start_time),
        attractions=attractions,
        end_time=float(end_time),
    )


def _resolve_handpicked_path(handpicked_file: str) -> Path:
    path = Path(handpicked_file)
    if path.is_absolute():
        return path
    conf_relative = CONF_ROOT / path
    if conf_relative.exists():
        return conf_relative
    return path


def _load_handpicked_rows(handpicked_file: str) -> list[dict[str, Any]]:
    resolved_path = _resolve_handpicked_path(handpicked_file)
    raw = OmegaConf.to_container(OmegaConf.load(resolved_path), resolve=True)
    if not isinstance(raw, dict):
        raise ValueError(f"handpicked file must contain a mapping: {resolved_path}")
    cases = raw.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError(f"handpicked cases must be a list: {resolved_path}")
    out: list[dict[str, Any]] = []
    seen_ids: dict[str, int] = {}
    for index, case in enumerate(cases, start=1):
        case_label = f"index={index}"
        if not isinstance(case, dict):
            raise ValueError(
                f"handpicked case must be a mapping: {resolved_path} (case={case_label})"
            )
        raw_id = case.get("id")
        if isinstance(raw_id, str) and raw_id.strip():
            case_label = raw_id.strip()
        try:
            parsed = HandpickedCaseRow.model_validate(case)
        except ValidationError as exc:
            first = exc.errors()[0]
            msg = str(first.get("msg", "invalid handpicked case"))
            raise ValueError(
                f"{msg}: {resolved_path} (case={case_label})"
            ) from None
        normalized_case_id = parsed.id
        if normalized_case_id in seen_ids:
            first_index = seen_ids[normalized_case_id]
            raise ValueError(
                "duplicate handpicked case id "
                f"'{normalized_case_id}': {resolved_path} "
                f"(first index={first_index}, duplicate index={index})"
            )
        seen_ids[normalized_case_id] = index
        row = parsed.model_dump(exclude_none=True)
        row["id"] = normalized_case_id
        out.append(row)
    return out


def _handpicked_cases(
    *,
    setup: SetupConfig,
    suite: SuiteConfig,
    fixture_cfg: FixtureMatrixConfig,
) -> list[Scenario]:
    out: list[Scenario] = []
    for row in _load_handpicked_rows(suite.handpicked_file):
        case_id = str(row["id"])
        seed = int(row["seed"])
        profile = str(row.get("profile", "relaxed"))
        if str(row.get("case_mode", "generated")) == "explicit":
            attractions_data = list(row["attractions"])
            start_time = int(row.get("start_time", setup.start_time))
            end_time = int(row.get("end_time", setup.end_time))
            n_attractions = len(attractions_data) + 1
            problem = _explicit_problem(
                setup=setup,
                seed=seed,
                start_time=start_time,
                end_time=end_time,
                attractions_data=attractions_data,
            )
        else:
            n_attractions = int(row["n_attractions"])
            problem = _generated_problem(
                n=n_attractions,
                profile=profile,
                seed=seed,
                setup=setup,
                fixture_cfg=fixture_cfg,
            )
        out.append(
            Scenario(
                id=case_id,
                seed=seed,
                n_attractions=n_attractions,
                profile=profile,
                suite=suite.name,
                setup_name=setup.name,
                problem=problem,
            )
        )
    return out


def build_scenarios(
    *,
    setup: SetupConfig,
    suite: SuiteConfig,
    fixture_cfg: FixtureMatrixConfig | None = None,
) -> list[Scenario]:
    cfg = fixture_cfg if fixture_cfg is not None else FixtureMatrixConfig()
    out: list[Scenario] = []
    for n in suite.n_attractions:
        for profile in suite.profiles:
            for seed_idx in range(suite.seed_count):
                seed = 1000 + n * 100 + seed_idx
                scenario_id = f"{suite.name}_{setup.name}_{profile}_n{n}_s{seed_idx}"
                out.append(
                    Scenario(
                        id=scenario_id,
                        seed=seed,
                        n_attractions=n,
                        profile=profile,
                        suite=suite.name,
                        setup_name=setup.name,
                        problem=_generated_problem(
                            n=n,
                            profile=profile,
                            seed=seed,
                            setup=setup,
                            fixture_cfg=cfg,
                        ),
                    )
                )
    if suite.include_handpicked:
        out.extend(_handpicked_cases(setup=setup, suite=suite, fixture_cfg=cfg))
    return out


def setup_from_dict(data: dict[str, Any], *, name: str) -> SetupConfig:
    return SetupConfig(
        name=name,
        start_time=int(data.get("start_time", 8 * 60)),
        end_time=int(data.get("end_time", 22 * 60)),
        min_stay=int(data.get("min_stay", 15)),
        extra_max=int(data.get("extra_max", 30)),
        base_lat=float(data.get("base_lat", 60.1700)),
        base_lon=float(data.get("base_lon", 24.9410)),
        location_spread=float(data.get("location_spread", 0.01)),
    )


def suite_from_dict(data: dict[str, Any], *, name: str) -> SuiteConfig:
    return SuiteConfig(
        name=name,
        variants=tuple(
            str(v) for v in data.get("variants", ["astar_greedy", "astar_intervals"])
        ),
        matrix_mode=str(data.get("matrix_mode", "fixture")),
        n_attractions=tuple(int(v) for v in data.get("n_attractions", [6, 9, 12])),
        seed_count=int(data.get("seed_count", 10)),
        profiles=tuple(str(v) for v in data.get("profiles", ["relaxed"])),
        include_handpicked=bool(data.get("include_handpicked", False)),
        handpicked_file=str(data.get("handpicked_file", "handpicked/boundary.yaml")),
    )
