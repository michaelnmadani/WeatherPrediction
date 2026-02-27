#!/usr/bin/env python3
"""
Phase 1: Collect weather forecasts for all NSW regions.
Runs early morning AEST to capture the day's forecast BEFORE the day unfolds.
Saves forecast data to data/forecasts/YYYY-MM-DD.json
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import requests

from config import NSW_REGIONS, FORECAST_API_URL, DAILY_VARIABLES, HOURLY_VARIABLES

AEST = timezone(timedelta(hours=10))


def fetch_forecast(region, target_date):
    """Fetch today's forecast for a single region from Open-Meteo."""
    params = {
        "latitude": region["lat"],
        "longitude": region["lon"],
        "daily": ",".join(DAILY_VARIABLES),
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "Australia/Sydney",
        "start_date": target_date,
        "end_date": target_date,
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "temperature_unit": "celsius",
    }

    resp = requests.get(FORECAST_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    hourly = data.get("hourly", {})

    # Calculate daily average humidity from hourly data
    humidity_values = hourly.get("relative_humidity_2m", [])
    avg_humidity = round(sum(humidity_values) / len(humidity_values), 1) if humidity_values else None

    return {
        "region": region["name"],
        "lat": region["lat"],
        "lon": region["lon"],
        "date": target_date,
        "high_temp": daily.get("temperature_2m_max", [None])[0],
        "low_temp": daily.get("temperature_2m_min", [None])[0],
        "wind_speed": daily.get("wind_speed_10m_max", [None])[0],
        "humidity": avg_humidity,
        "rain": daily.get("precipitation_sum", [None])[0],
    }


def main():
    # Target date is today in AEST
    now_aest = datetime.now(AEST)
    target_date = now_aest.strftime("%Y-%m-%d")

    print(f"Collecting forecasts for {target_date} (AEST)")
    print(f"Current time: {now_aest.isoformat()}")

    forecasts = []
    for region in NSW_REGIONS:
        try:
            forecast = fetch_forecast(region, target_date)
            forecasts.append(forecast)
            print(f"  OK: {region['name']} - High: {forecast['high_temp']}°C, "
                  f"Low: {forecast['low_temp']}°C, Rain: {forecast['rain']}mm")
        except Exception as e:
            print(f"  FAIL: {region['name']} - {e}", file=sys.stderr)

        # Rate limiting - be kind to the free API
        time.sleep(0.5)

    output = {
        "date": target_date,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "type": "forecast",
        "region_count": len(forecasts),
        "regions": forecasts,
    }

    # Save to data/forecasts/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    output_dir = os.path.join(repo_root, "data", "forecasts")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{target_date}.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved {len(forecasts)} forecasts to {output_path}")
    return 0 if len(forecasts) == len(NSW_REGIONS) else 1


if __name__ == "__main__":
    sys.exit(main())
