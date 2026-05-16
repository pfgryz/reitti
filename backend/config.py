# Pedestrian speed
PEDESTRIAN_SPEED = 5.0  # 5 km/h

# Maximum travel time and distance to public transport
MAX_TRAVEL_TIME_TO_PUBLIC_TRANSPORT = 1 / 6  # 10 minutes
MAX_TRAVEL_DISTANCE_TO_PUBLIC_TRANSPORT = (
    MAX_TRAVEL_TIME_TO_PUBLIC_TRANSPORT * PEDESTRIAN_SPEED * 1000  # Convert to meters
)

# Maximum number of stops in a single query / PT routing search
MAX_STOPS_QUERY_COUNT = 20
MAX_PUBLIC_TRANSPORT_STOPS_TO_CONSIDER = MAX_STOPS_QUERY_COUNT
