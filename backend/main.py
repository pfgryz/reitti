import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
import httpx
from app.frontend import mount_frontend
from app.routers import distance, stops, trip
from core.exceptions import ConfigurationError, RouteNotFoundError
from core.route_cache import RouteCache
from core.routing import RouteSummary, RoutingError
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

load_dotenv(Path(__file__).with_name(".env"))

logger = logging.getLogger("uvicorn.access")


def _client_addr(request: Request) -> str:
    if request.client is None:
        return "-"
    return f"{request.client.host}:{request.client.port}"


def _request_target(request: Request) -> str:
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"
    return path


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Configure it in backend/.env")

    app.state.db_pool = await asyncpg.create_pool(
        dsn=database_url, min_size=1, max_size=10
    )
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    app.state.route_cache: RouteCache[RouteSummary] = RouteCache()

    try:
        yield
    finally:
        await app.state.http_client.aclose()
        await app.state.db_pool.close()


app = FastAPI(lifespan=lifespan)
app.include_router(distance.router)
app.include_router(stops.router)
app.include_router(trip.router)
mount_frontend(app)


@app.middleware("http")
async def log_request_duration(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    http_version = request.scope.get("http_version", "1.1")
    logger.info(
        '%s - "%s %s HTTP/%s" %s %.2fms',
        _client_addr(request),
        request.method,
        _request_target(request),
        http_version,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(RouteNotFoundError)
async def route_not_found_handler(_request: Request, exc: RouteNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": {"code": exc.code.value, "message": exc.message}},
    )


@app.exception_handler(RoutingError)
async def routing_error_handler(_request: Request, exc: RoutingError):
    return JSONResponse(
        status_code=502,
        content={"detail": {"code": "GRAPHHOPPER_ERROR", "message": str(exc)}},
    )


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(_request: Request, exc: ConfigurationError):
    return JSONResponse(
        status_code=500,
        content={"detail": {"code": "CONFIGURATION_ERROR", "message": exc.message}},
    )


@app.get("/")
async def root():
    return {"message": "Hello, World!"}
