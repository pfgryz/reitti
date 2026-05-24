import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/places", tags=["places"])

PLACES_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "places.json"


@router.get("")
def list_places() -> list[dict]:
    if not PLACES_FILE.is_file():
        raise HTTPException(
            status_code=503,
            detail="Missing places.json. Run: just extract-places",
        )
    return json.loads(PLACES_FILE.read_text(encoding="utf-8"))
