import httpx
from asyncpg import Pool
from core.route_cache import RouteCache
from core.routing import RouteSummary
from fastapi import Request


async def get_db(request: Request) -> Pool:
    return request.app.state.db_pool


async def get_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


async def get_route_cache(request: Request) -> RouteCache[RouteSummary]:
    return request.app.state.route_cache
