import os
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
import httpx
from app.routers import distance, stops
from core.exceptions import RouteNotFoundError
from core.route_cache import RouteCache
from core.routing import RouteSummary
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

load_dotenv(Path(__file__).with_name(".env"))


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


@app.exception_handler(RouteNotFoundError)
async def route_not_found_handler(_request: Request, exc: RouteNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": {"code": exc.code.value, "message": exc.message}},
    )


@app.get("/")
async def root():
    return {"message": "Hello, World!"}
