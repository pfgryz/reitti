import os
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
from app.routers import distance, stops
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv(Path(__file__).with_name(".env"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Configure it in backend/.env")

    app.state.db_pool = await asyncpg.create_pool(
        dsn=database_url, min_size=1, max_size=10
    )

    try:
        yield
    finally:
        await app.state.db_pool.close()


app = FastAPI(lifespan=lifespan)
app.include_router(distance.router)
app.include_router(stops.router)


@app.get("/")
async def root():
    return {"message": "Hello, World!"}
