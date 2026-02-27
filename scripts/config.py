"""
Configuration for NSW Weather Accuracy Tracker.
Defines all NSW regions with their coordinates for Open-Meteo API calls.
"""

# NSW regions with representative city coordinates (latitude, longitude)
NSW_REGIONS = [
    {"name": "Sydney", "lat": -33.87, "lon": 151.21},
    {"name": "Newcastle", "lat": -32.93, "lon": 151.78},
    {"name": "Wollongong", "lat": -34.42, "lon": 150.89},
    {"name": "Central Coast", "lat": -33.43, "lon": 151.34},
    {"name": "Blue Mountains", "lat": -33.72, "lon": 150.31},
    {"name": "Penrith", "lat": -33.75, "lon": 150.69},
    {"name": "Broken Hill", "lat": -31.95, "lon": 141.45},
    {"name": "Dubbo", "lat": -32.24, "lon": 148.60},
    {"name": "Tamworth", "lat": -31.09, "lon": 150.93},
    {"name": "Coffs Harbour", "lat": -30.30, "lon": 153.11},
    {"name": "Lismore", "lat": -28.81, "lon": 153.28},
    {"name": "Wagga Wagga", "lat": -35.12, "lon": 147.37},
    {"name": "Albury", "lat": -36.08, "lon": 146.92},
    {"name": "Orange", "lat": -33.28, "lon": 149.10},
    {"name": "Bathurst", "lat": -33.42, "lon": 149.58},
    {"name": "Griffith", "lat": -34.29, "lon": 146.04},
    {"name": "Armidale", "lat": -30.51, "lon": 151.67},
    {"name": "Port Macquarie", "lat": -31.43, "lon": 152.91},
    {"name": "Nowra", "lat": -34.88, "lon": 150.60},
    {"name": "Moree", "lat": -29.46, "lon": 149.85},
]

# Open-Meteo API base URLs
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_API_URL = "https://archive-api.open-meteo.com/v1/archive"
BOM_API_URL = "https://api.open-meteo.com/v1/bom"

# Daily variables to request
DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
]

# Hourly variables (needed for humidity - no daily aggregate available)
HOURLY_VARIABLES = [
    "relative_humidity_2m",
]

# Accuracy thresholds for each metric
THRESHOLDS = {
    "high_temp": {"exact": 0, "near": 2, "wide": 4, "unit": "°C"},
    "low_temp": {"exact": 0, "near": 2, "wide": 4, "unit": "°C"},
    "wind_speed": {"exact": 0, "near": 1, "wide": 10, "unit": "km/h"},
    "humidity": {"exact": 0, "near": 5, "wide": 10, "unit": "%"},
    "rain": {"exact": 0, "near": 1, "wide": 5, "unit": "mm"},
}
