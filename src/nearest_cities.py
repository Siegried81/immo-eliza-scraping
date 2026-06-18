
import math

# ---------------------------------------
# MAJOR CITIES
# ---------------------------------------
CITIES = {
    "Antwerp": (51.2194, 4.4025),
    "Brussels": (50.8467, 4.3499),
    "Ghent": (51.0543, 3.7174),
    "Charleroi": (50.4108, 4.4446),
    "Liege": (50.6451, 5.5734),
    "Bruges": (51.2093, 3.2247),
    "Namur": (50.4674, 4.8719),
    "Leuven": (50.8798, 4.7005),
}


# ---------------------------------------
# HAVERSINE
# ---------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0088

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dlon / 2) ** 2
    )

    return 2 * R * math.asin(math.sqrt(a))


def nearest_city(lat, lon):
    best_city = None
    best_dist = float("inf")

    for city, (clat, clon) in CITIES.items():
        d = haversine(lat, lon, clat, clon)

        if d < best_dist:
            best_city = city
            best_dist = d

    return best_city, round(best_dist, 2)


if __name__ == "__main__":
    pass