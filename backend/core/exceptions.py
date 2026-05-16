from enum import Enum


class RouteNotFoundCode(str, Enum):
    NO_STOPS_NEAR_ORIGIN = "NO_STOPS_NEAR_ORIGIN"
    NO_STOPS_NEAR_DESTINATION = "NO_STOPS_NEAR_DESTINATION"
    NO_TRANSIT_LEGS = "NO_TRANSIT_LEGS"
    ALL_CANDIDATES_PRUNED = "ALL_CANDIDATES_PRUNED"
    NO_VIABLE_ROUTE = "NO_VIABLE_ROUTE"
    NO_STOPS_FOUND = "NO_STOPS_FOUND"


class RouteNotFoundError(Exception):
    def __init__(self, code: RouteNotFoundCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)
