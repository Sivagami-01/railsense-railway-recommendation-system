"""
Station Cleaning Script
-----------------------
Cleans stations.json by removing invalid/placeholder records (codes starting with 'XX-'
or (0,0) coordinates) and duplicate station codes, printing a summary, and saving
the result to stations_clean.json.
"""

import json
import os
from typing import Optional


def clean_stations(input_file_path: Optional[str] = None) -> None:
    """
    Loads stations.json, filters out placeholder entries, removes duplicate station codes,
    prints summary stats, and writes the output to stations_clean.json in the same folder.

    Args:
        input_file_path: Optional path to stations.json. If None, checks current directory
                         and dataset/ directory.
    """
    if input_file_path is None:
        if os.path.exists("stations.json"):
            input_file_path = "stations.json"
        elif os.path.exists(os.path.join("dataset", "stations.json")):
            input_file_path = os.path.join("dataset", "stations.json")
        else:
            raise FileNotFoundError("stations.json not found in the current folder or 'dataset/' folder.")

    input_file_path = os.path.abspath(input_file_path)
    output_dir = os.path.dirname(input_file_path)
    output_file_path = os.path.join(output_dir, "stations_clean.json")

    with open(input_file_path, "r", encoding="utf-8") as f:
        stations = json.load(f)

    total_before = len(stations)
    cleaned_stations = []
    seen_codes = set()

    for station in stations:
        code = str(station.get("code", "") or "").strip()
        
        coords = station.get("coordinates") or {}
        longitude = coords.get("longitude", 0) if isinstance(coords, dict) else 0
        latitude = coords.get("latitude", 0) if isinstance(coords, dict) else 0

        # Filter criteria: remove record if any condition is met
        # 1. code starts with "XX-"
        if code.startswith("XX-"):
            continue

        # 2. coordinates.longitude == 0 AND coordinates.latitude == 0
        if longitude == 0 and latitude == 0:
            continue

        # 3. Remove exact duplicate station codes (keep the first occurrence)
        if code in seen_codes:
            continue

        seen_codes.add(code)
        cleaned_stations.append(station)

    total_remaining = len(cleaned_stations)
    total_removed = total_before - total_remaining

    print("=== Stations Dataset Cleaning Summary ===")
    print(f"Total records before   : {total_before}")
    print(f"Total records removed  : {total_removed}")
    print(f"Total records remaining: {total_remaining}")

    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_stations, f, indent=2, ensure_ascii=False)

    print(f"Cleaned dataset saved as: {output_file_path}")


if __name__ == "__main__":
    clean_stations()
