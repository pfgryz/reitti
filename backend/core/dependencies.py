import httpx
from fastapi import Request


async def get_db(request: Request):
    return request.app.state.db_pool


async def get_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client
