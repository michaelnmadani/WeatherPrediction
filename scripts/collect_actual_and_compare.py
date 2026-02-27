#!/usr/bin/env python3
"""
Phase 2: Collect actual weather for the previous day and compare to forecast.
Runs shortly after midnight AEST to get yesterday's actual weather.
Loads the corresponding forecast, computes accuracy, and saves results.
Also rebuilds the summary JSON used by the frontend.
"""

import json
import math
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import requests

from config import (
    NSW_REGIONS, FORECAST_API_URL, DAILY_VARIABLES, HOURLY_VARIABLES, THRESHOLDS
)

AEST = timezone(timedelta(hours=10))
METRICS = ["high_temp", "low_temp", "wind_speed", "humidity", "rain"]


def fetch_actual(region, target_date):
    """Fetch actual weather for a completed day using Open-Meteo forecast API with past_days.

    We use the forecast API (not historical archive) because the archive API
    has a multi-day delay. The forecast API's past_days data uses data
    assimilation from weather stations, giving us near-observed values for
    recent days.
    """
    params = {
        "latitude": region["lat"],
        "longitude": region["lon"],
        "daily": ",".join(DAILY_VARIABLES),
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "Australia/Sydney",
        "start_date": target_date,
        "end_date": target_date,
        "past_days": 2,
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "temperature_unit": "celsius",
    }

    resp = requests.get(FORECAST_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    hourly = data.get("hourly", {})

    # Find the index for our target date in the daily arrays
    daily_dates = daily.get("time", [])
    try:
        idx = daily_dates.index(target_date)
    except ValueError:
        raise ValueError(f"Target date {target_date} not found in API response dates: {daily_dates}")

    # For hourly humidity, extract only the 24 hours for the target date
    hourly_times = hourly.get("time", [])
    humidity_values = hourly.get("relative_humidity_2m", [])
    day_humidity = []
    for i, t in enumerate(hourly_times):
        if t.startswith(target_date) and i < len(humidity_values) and humidity_values[i] is not None:
            day_humidity.append(humidity_values[i])

    avg_humidity = round(sum(day_humidity) / len(day_humidity), 1) if day_humidity else None

    return {
        "region": region["name"],
        "lat": region["lat"],
        "lon": region["lon"],
        "date": target_date,
        "high_temp": daily.get("temperature_2m_max", [None])[idx],
        "low_temp": daily.get("temperature_2m_min", [None])[idx],
        "wind_speed": daily.get("wind_speed_10m_max", [None])[idx],
        "humidity": avg_humidity,
        "rain": daily.get("precipitation_sum", [None])[idx],
    }


def compute_accuracy(forecast_regions, actual_regions):
    """Compare forecast vs actual for each region and compute accuracy metrics."""
    # Index actuals by region name for easy lookup
    actual_by_name = {a["region"]: a for a in actual_regions}

    comparisons = []
    diffs = {m: [] for m in METRICS}

    for fc in forecast_regions:
        name = fc["region"]
        act = actual_by_name.get(name)
        if not act:
            continue

        region_comp = {"region": name, "metrics": {}}

        for metric in METRICS:
            fc_val = fc.get(metric)
            act_val = act.get(metric)

            if fc_val is None or act_val is None:
                region_comp["metrics"][metric] = {
                    "forecast": fc_val,
                    "actual": act_val,
                    "diff": None,
                }
                continue

            diff = round(abs(fc_val - act_val), 2)
            diffs[metric].append(diff)
            region_comp["metrics"][metric] = {
                "forecast": fc_val,
                "actual": act_val,
                "diff": diff,
            }

        comparisons.append(region_comp)

    # Compute summary statistics
    summary = {}
    for metric in METRICS:
        vals = diffs[metric]
        if not vals:
            summary[metric] = None
            continue

        thresholds = THRESHOLDS[metric]
        n = len(vals)

        exact_count = sum(1 for v in vals if v <= 0.5)  # within rounding
        near_count = sum(1 for v in vals if v <= thresholds["near"])
        wide_count = sum(1 for v in vals if v <= thresholds["wide"])

        mean_diff = sum(vals) / n
        std_dev = math.sqrt(sum((v - mean_diff) ** 2 for v in vals) / n) if n > 1 else 0

        summary[metric] = {
            "exact_pct": round(exact_count / n * 100, 1),
            "near_pct": round(near_count / n * 100, 1),
            "near_threshold": thresholds["near"],
            "wide_pct": round(wide_count / n * 100, 1),
            "wide_threshold": thresholds["wide"],
            "mean_diff": round(mean_diff, 2),
            "std_dev": round(std_dev, 2),
            "unit": thresholds["unit"],
            "sample_size": n,
        }

    # Overall score: average of the "wide" percentage across all metrics (higher = better)
    valid_summaries = [s for s in summary.values() if s is not None]
    overall_score = round(
        sum(s["wide_pct"] for s in valid_summaries) / len(valid_summaries), 1
    ) if valid_summaries else 0

    # Weighted overall score using std_dev (lower std_dev = more consistent = bonus)
    avg_std = sum(s["std_dev"] for s in valid_summaries) / len(valid_summaries) if valid_summaries else 0

    return {
        "summary": summary,
        "overall_score": overall_score,
        "avg_std_dev": round(avg_std, 2),
        "comparisons": comparisons,
    }


def rebuild_summary(results_dir):
    """Rebuild the summary.json used by the frontend from all result files."""
    all_results = []

    for filename in sorted(os.listdir(results_dir)):
        if not filename.endswith(".json") or filename == "summary.json":
            continue
        filepath = os.path.join(results_dir, filename)
        with open(filepath) as f:
            result = json.load(f)
        all_results.append({
            "date": result["date"],
            "overall_score": result["accuracy"]["overall_score"],
            "avg_std_dev": result["accuracy"]["avg_std_dev"],
            "summary": result["accuracy"]["summary"],
        })

    # Sort by date descending (most recent first)
    all_results.sort(key=lambda x: x["date"], reverse=True)

    summary = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_days": len(all_results),
        "results": all_results,
    }

    summary_path = os.path.join(results_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Rebuilt summary.json with {len(all_results)} days of data")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)

    # Yesterday in AEST
    now_aest = datetime.now(AEST)
    yesterday = (now_aest - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Processing results for {yesterday}")
    print(f"Current time: {now_aest.isoformat()}")

    # Load forecast for yesterday
    forecast_path = os.path.join(repo_root, "data", "forecasts", f"{yesterday}.json")
    if not os.path.exists(forecast_path):
        print(f"ERROR: No forecast file found for {yesterday} at {forecast_path}")
        print("Cannot compare without a forecast. Exiting.")
        return 1

    with open(forecast_path) as f:
        forecast_data = json.load(f)

    # Collect actual weather for yesterday
    print(f"\nCollecting actual weather for {yesterday}...")
    actuals = []
    for region in NSW_REGIONS:
        try:
            actual = fetch_actual(region, yesterday)
            actuals.append(actual)
            print(f"  OK: {region['name']} - High: {actual['high_temp']}°C, "
                  f"Low: {actual['low_temp']}°C, Rain: {actual['rain']}mm")
        except Exception as e:
            print(f"  FAIL: {region['name']} - {e}", file=sys.stderr)
        time.sleep(0.5)

    # Save actuals
    actuals_dir = os.path.join(repo_root, "data", "actuals")
    os.makedirs(actuals_dir, exist_ok=True)
    actuals_output = {
        "date": yesterday,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "type": "actual",
        "region_count": len(actuals),
        "regions": actuals,
    }
    actuals_path = os.path.join(actuals_dir, f"{yesterday}.json")
    with open(actuals_path, "w") as f:
        json.dump(actuals_output, f, indent=2)
    print(f"\nSaved {len(actuals)} actuals to {actuals_path}")

    # Compute accuracy
    print("\nComputing accuracy...")
    accuracy = compute_accuracy(forecast_data["regions"], actuals)

    # Print summary
    print("\n=== ACCURACY SUMMARY ===")
    for metric in METRICS:
        s = accuracy["summary"].get(metric)
        if not s:
            print(f"  {metric}: No data")
            continue
        labels = {
            "high_temp": "High Temp",
            "low_temp": "Low Temp",
            "wind_speed": "Wind Speed",
            "humidity": "Humidity",
            "rain": "Rain",
        }
        label = labels.get(metric, metric)
        print(f"  {label}: {s['exact_pct']}% Exact | "
              f"{s['near_pct']}% within {s['near_threshold']}{s['unit']} | "
              f"{s['wide_pct']}% within {s['wide_threshold']}{s['unit']} | "
              f"StdDev: {s['std_dev']}{s['unit']}")

    print(f"\n  Overall Score: {accuracy['overall_score']}%")
    print(f"  Average Std Dev: {accuracy['avg_std_dev']}")

    # Save result
    results_dir = os.path.join(repo_root, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    result = {
        "date": yesterday,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "forecast_collected_at": forecast_data.get("collected_at"),
        "accuracy": accuracy,
    }
    result_path = os.path.join(results_dir, f"{yesterday}.json")
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved results to {result_path}")

    # Rebuild summary for frontend
    rebuild_summary(results_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
