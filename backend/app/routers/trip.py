import httpx
from asyncpg import Pool
from app.schemas.trip import TripOptimizeRequest, TripOptimizeResponse, from_result
from core.dependencies import get_client, get_db, get_route_cache
from core.route_cache import RouteCache
from core.route_optimizer import create_travel_matrices, optimize_route
from core.routing import RouteSummary
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/trip", tags=["trip"])


@router.post("/optimize", response_model=TripOptimizeResponse)
async def optimize_trip(
    body: TripOptimizeRequest,
    client: httpx.AsyncClient = Depends(get_client),
    db: Pool = Depends(get_db),
    route_cache: RouteCache[RouteSummary] = Depends(get_route_cache),
) -> TripOptimizeResponse:
    problem = body.to_problem()
    matrices = create_travel_matrices(
        problem.attractions,
        client=client,
        db=db,
        route_cache=route_cache,
    )
    result = await optimize_route(problem, matrices)
    return await from_result(
        result,
        matrices,
        problem.attractions,
        include_legs=body.include_legs,
        client=client,
        route_cache=route_cache,
    )
