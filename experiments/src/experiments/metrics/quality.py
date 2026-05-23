from __future__ import annotations

from .utils import ALPHA, BETA


async def walk_total(visits: tuple, matrices) -> float:
    total = 0.0
    current = 0
    for visit in visits:
        nxt = visit.attraction_index
        total += await matrices.walk_dist.get(current, nxt)
        current = nxt
    return total


def quality(
    problem, visits: tuple, walk_distance_m: float
) -> tuple[float, float, float]:
    total_stay = sum(v.departure_time - v.arrival_time for v in visits)
    used = {v.attraction_index: v.departure_time - v.arrival_time for v in visits}
    total_max = sum(a.stay.max for a in problem.attractions[1:])
    unused = problem.attractions[0].stay.max
    for idx, attraction in enumerate(problem.attractions):
        if idx == 0:
            continue
        unused += attraction.stay.max - used.get(idx, 0.0)
    stay_utilization = (total_stay / total_max) if total_max > 0 else 1.0
    objective = ALPHA * walk_distance_m + BETA * unused
    return total_stay, stay_utilization, objective
