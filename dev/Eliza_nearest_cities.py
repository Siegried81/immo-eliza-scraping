import pandas as pd
import math
import os
import logging

# ---------------------------------------
# LOGGING 
# ---------------------------------------
logger = logging.getLogger('main_logger')
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - INFO - %(message)s'))

if not logger.handlers:
    logger.addHandler(handler)


# ---------------------------------------
# PATHS
# ---------------------------------------
# FIX: script is in /dev but data is written in project root (immo-eliza-scraping/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(BASE_DIR, "data/dataframe.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "data/dataframe_enriched.json")


# ---------------------------------------
# MAJOR CITIES
# ---------------------------------------
CITIES = {
    "Antwerp": (51.2194, 4.4025),
    "Brussels": (50.8467, 4.3499),
    "Ghent": (51.0543, 3.7174),
    "Charleroi": (50.4108, 4.4446),
    "Liège": (50.6451, 5.5734),
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


# ---------------------------------------
# MAIN
# ---------------------------------------
def main():

    if not os.path.exists(INPUT_FILE):
        logger.error("No input file found")
        logger.error("Expected path: %s", INPUT_FILE)
        return

    df = pd.read_json(INPUT_FILE)

    if df.empty:
        logger.error("Empty dataset")
        return

    logger.info("Postprocessing started...")

    # -------------------------------
    # SAFE TYPE CLEANING (important)
    # -------------------------------
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    cities = []
    distances = []

    # -------------------------------
    # FAST & SAFE ITERATION
    # -------------------------------
    for row in df.itertuples(index=False):

        lat = row.latitude
        lon = row.longitude

        if pd.isna(lat) or pd.isna(lon):
            cities.append(None)
            distances.append(None)
            continue

        city, dist = nearest_city(float(lat), float(lon))
        cities.append(city)
        distances.append(dist)

    df["nearest_city"] = cities
    df["nearest_city_distance_km"] = distances

    # -------------------------------
    # OUTPUT
    # -------------------------------
    df.to_json(
        OUTPUT_FILE,
        orient="records",
        force_ascii=False,
        indent=2
    )

    logger.info("Saved enriched dataset -> %s", OUTPUT_FILE)
    logger.info("Rows processed: %d", len(df))


if __name__ == "__main__":
    main()