import httpx
from fastapi import Request


async def get_db(request: Request):
    return request.app.state.db_pool


async def get_client(request: Request):
    return httpx.AsyncClient(timeout=30.0)
