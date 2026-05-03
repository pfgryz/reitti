# Pedestrian speed
PEDESTRIAN_SPEED = 5.0  # 5 km/h

# Maximum travel time and distance to public transport
MAX_TRAVEL_TIME_TO_PUBLIC_TRANSPORT = 1 / 6  # 10 minutes
MAX_TRAVEL_DISTANCE_TO_PUBLIC_TRANSPORT = (
    MAX_TRAVEL_TIME_TO_PUBLIC_TRANSPORT * PEDESTRIAN_SPEED * 1000  # Convert to meters
)

# Maximum number of public transport stops to consider
MAX_PUBLIC_TRANSPORT_STOPS_TO_CONSIDER = 20
