from app.schemas.trip import TripOptimizeRequest, TripOptimizeResponse
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/trip", tags=["trip"])


@router.post("/optimize", response_model=TripOptimizeResponse)
async def optimize_trip(_body: TripOptimizeRequest) -> TripOptimizeResponse:
    raise HTTPException(status_code=501, detail="not implemented")
