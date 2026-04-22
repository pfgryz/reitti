from app.routers import stops
from fastapi import FastAPI

app = FastAPI()

app.include_router(stops.router)


@app.get("/")
async def root():
    return {"message": "Hello, World!"}
