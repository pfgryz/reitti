from pydantic import BaseModel


class Stop(BaseModel):
    name: str
    lat: float
    lon: float


async def get_nearest_stop(lat: float, lon: float) -> Stop:
    return (await get_nearest_stops(lat, lon, count=1))[0]


async def get_nearest_stops(lat: float, lon: float, count: int = 10) -> list[Stop]:
    return [
        Stop(name="Test", lat=lat, lon=lon)
    ]  # @TODO: Implement actual nearest stops logic
