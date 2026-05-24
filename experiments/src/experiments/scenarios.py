from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from omegaconf import OmegaConf
from pydantic import BaseModel, ConfigDict, StrictInt, ValidationError, model_validator

from . import ensure_backend_path

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
    open_start_min: int
    open_start_max: int
    window_len_min: int
    window_len_max: int
    min_stay_min: int
    min_stay_max: int
    extra_max_min: int
    extra_max_max: int
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


def _sample_window(
    profile: str, rng: random.Random, setup: SetupConfig
) -> tuple[int, int]:
    if profile == "impossible":
        open_at = rng.randint(setup.end_time - 240, setup.end_time - 120)
        return open_at, open_at + rng.randint(15, 30)
    if profile == "tight":
        open_at = rng.randint(setup.open_start_min + 60, setup.open_start_max + 120)
        return open_at, open_at + rng.randint(60, 120)
    open_at = rng.randint(setup.open_start_min, setup.open_start_max)
    return open_at, open_at + rng.randint(setup.window_len_min, setup.window_len_max)


def _sample_stay(
    profile: str, rng: random.Random, setup: SetupConfig
) -> tuple[int, int]:
    min_stay = rng.randint(setup.min_stay_min, setup.min_stay_max)
    extra = rng.randint(setup.extra_max_min, setup.extra_max_max)
    max_stay = min_stay + extra
    if profile == "impossible":
        min_stay = max(min_stay, 30)
        max_stay = max(max_stay, min_stay + 10)
    return min_stay, max_stay


def _build_problem(
    *,
    n_attractions: int,
    profile: str,
    seed: int,
    setup: SetupConfig,
) -> RouteOptimizationInput:
    rng = random.Random(seed)
    attractions = [
        _attraction(
            lat=setup.base_lat,
            lon=setup.base_lon,
            open_at=0.0,
            close_at=24 * 60,
            min_stay=0.0,
            max_stay=0.0,
        )
    ]
    for _ in range(1, n_attractions):
        open_at, close_at = _sample_window(profile, rng, setup)
        min_stay, max_stay = _sample_stay(profile, rng, setup)
        attractions.append(
            _attraction(
                lat=setup.base_lat
                + rng.uniform(-setup.location_spread, setup.location_spread),
                lon=setup.base_lon
                + rng.uniform(-setup.location_spread, setup.location_spread),
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


def _build_explicit_problem(
    *,
    setup: SetupConfig,
    seed: int,
    start_time: int,
    end_time: int,
    attractions_data: list[dict[str, Any]],
) -> RouteOptimizationInput:
    rng = random.Random(seed)
    attractions = [
        _attraction(
            lat=setup.base_lat,
            lon=setup.base_lon,
            open_at=0.0,
            close_at=24 * 60,
            min_stay=0.0,
            max_stay=0.0,
        )
    ]
    for row in attractions_data:
        attractions.append(
            _attraction(
                lat=setup.base_lat
                + rng.uniform(-setup.location_spread, setup.location_spread),
                lon=setup.base_lon
                + rng.uniform(-setup.location_spread, setup.location_spread),
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


def _build_boundary_all_impossible(
    *, setup: SetupConfig, seed: int
) -> RouteOptimizationInput:
    return _build_problem(
        n_attractions=8,
        profile="impossible",
        seed=seed,
        setup=setup,
    )


def _build_boundary_single_unreachable(
    *, setup: SetupConfig, seed: int
) -> RouteOptimizationInput:
    problem = _build_problem(
        n_attractions=6,
        profile="relaxed",
        seed=seed,
        setup=setup,
    )
    unreachable = _attraction(
        lat=problem.attractions[1].position.lat,
        lon=problem.attractions[1].position.lon,
        open_at=float(setup.start_time + 30),
        close_at=float(setup.start_time + 35),
        min_stay=10.0,
        max_stay=15.0,
    )
    attractions = [problem.attractions[0], unreachable, *problem.attractions[2:]]
    return RouteOptimizationInput(
        start_time=problem.start_time,
        attractions=attractions,
        end_time=problem.end_time,
    )


def _build_boundary_empty_only_start(
    *, setup: SetupConfig, seed: int
) -> RouteOptimizationInput:
    return _build_problem(
        n_attractions=1,
        profile="relaxed",
        seed=seed,
        setup=setup,
    )


def _build_boundary_timeout_bf(
    *, setup: SetupConfig, seed: int
) -> RouteOptimizationInput:
    return _build_problem(
        n_attractions=10,
        profile="relaxed",
        seed=seed,
        setup=setup,
    )


_HANDPICKED_BOUNDARY_BUILDERS: dict[
    str,
    tuple[str, int, Callable[[SetupConfig, int], RouteOptimizationInput]],
] = {
    "boundary_all_impossible": ("impossible", 8, _build_boundary_all_impossible),
    "boundary_single_unreachable": ("relaxed", 6, _build_boundary_single_unreachable),
    "boundary_empty_only_start": ("relaxed", 1, _build_boundary_empty_only_start),
    "boundary_timeout_bf": ("relaxed", 10, _build_boundary_timeout_bf),
}


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
        case_label = f"index={index}"
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


def _handpicked_cases(*, setup: SetupConfig, suite: SuiteConfig) -> list[Scenario]:
    rows = _load_handpicked_rows(suite.handpicked_file)
    out: list[Scenario] = []
    for row in rows:
        case_id = str(row["id"])
        seed = int(row["seed"])
        case_mode = str(row.get("case_mode", "generated"))
        boundary_override = _HANDPICKED_BOUNDARY_BUILDERS.get(case_id)
        if case_mode == "explicit":
            profile = str(row.get("profile", "relaxed"))
            attractions_data = list(row["attractions"])
            start_time = int(row.get("start_time", setup.start_time))
            end_time = int(row.get("end_time", setup.end_time))
            n_attractions = len(attractions_data) + 1
            problem = _build_explicit_problem(
                setup=setup,
                seed=seed,
                start_time=start_time,
                end_time=end_time,
                attractions_data=attractions_data,
            )
        elif boundary_override is not None:
            profile, n_attractions, builder = boundary_override
            problem = builder(setup=setup, seed=seed)
        else:
            profile = str(row.get("profile", "relaxed"))
            n_attractions = int(row["n_attractions"])
            problem = _build_problem(
                n_attractions=n_attractions,
                profile=profile,
                seed=seed,
                setup=setup,
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


def build_scenarios(*, setup: SetupConfig, suite: SuiteConfig) -> list[Scenario]:
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
                        problem=_build_problem(
                            n_attractions=n,
                            profile=profile,
                            seed=seed,
                            setup=setup,
                        ),
                    )
                )
    if suite.include_handpicked:
        out.extend(_handpicked_cases(setup=setup, suite=suite))
    return out


def setup_from_dict(data: dict[str, Any], *, name: str) -> SetupConfig:
    return SetupConfig(
        name=name,
        start_time=int(data.get("start_time", 8 * 60)),
        end_time=int(data.get("end_time", 22 * 60)),
        open_start_min=int(data.get("open_start_min", 8 * 60)),
        open_start_max=int(data.get("open_start_max", 11 * 60)),
        window_len_min=int(data.get("window_len_min", 180)),
        window_len_max=int(data.get("window_len_max", 600)),
        min_stay_min=int(data.get("min_stay_min", 10)),
        min_stay_max=int(data.get("min_stay_max", 30)),
        extra_max_min=int(data.get("extra_max_min", 10)),
        extra_max_max=int(data.get("extra_max_max", 60)),
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
