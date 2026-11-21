"""
MongoDB Import Script for Train Recommendation System
------------------------------------------------------
Imports stations_clean.json, trains.json, and ir_train.csv into local MongoDB database.

Database Name: train_recommendation_system
Collections:
  - stations (unique index on 'code')
  - trains (unique index on 'trainNumber')
  - delay_history (bulk inserted from ir_train.csv with error handling)
"""

import json
import os
import sys
import time
from collections import defaultdict
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

# Configure stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Configuration Constants
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "train_recommendation_system"
REPORT_FILENAME = "missing_stations_report.txt"


def resolve_file_path(filename: str) -> str:
    """Finds a file in current directory or dataset/ directory."""
    if os.path.exists(filename):
        return os.path.abspath(filename)
    dataset_path = os.path.join("dataset", filename)
    if os.path.exists(dataset_path):
        return os.path.abspath(dataset_path)
    raise FileNotFoundError(f"Required file '{filename}' not found in '.' or 'dataset/'.")


def main():
    print("=================================================================")
    print("   TRAIN RECOMMENDATION SYSTEM - MONGODB DATA IMPORT TOOL")
    print("=================================================================")

    # 1. Connect to MongoDB
    print(f"\n[1/4] Connecting to MongoDB at '{MONGO_URI}'...")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("[OK] Connected successfully to MongoDB server.")
    except Exception as e:
        print(f"[ERROR] Failed to connect to MongoDB: {e}")
        print("Please ensure your local MongoDB service is running on port 27017.")
        sys.exit(1)

    db = client[DB_NAME]

    # Resolve Data File Paths
    stations_path = resolve_file_path("stations_clean.json")
    trains_path = resolve_file_path("trains.json")

    try:
        csv_path = resolve_file_path("ir_train.csv")
    except FileNotFoundError:
        csv_path = resolve_file_path("trains.csv")

    print("\nData files resolved:")
    print(f"  - Stations: {stations_path}")
    print(f"  - Trains  : {trains_path}")
    print(f"  - CSV     : {csv_path}")

    # -----------------------------------------------------------------
    # STEP 2: Import Stations Collection
    # -----------------------------------------------------------------
    print("\n[2/4] Importing 'stations' collection...")
    stations_col = db["stations"]
    stations_col.drop()  # Reset collection for clean re-run
    stations_col.create_index("code", unique=True)

    with open(stations_path, "r", encoding="utf-8") as f:
        stations_data = json.load(f)

    valid_station_codes = set()
    for station in stations_data:
        code = station.get("code")
        if code:
            valid_station_codes.add(code)

    if stations_data:
        stations_col.insert_many(stations_data)

    total_stations_inserted = len(stations_data)
    print(f"[OK] Inserted {total_stations_inserted:,} station documents into 'stations' collection.")
    print("[OK] Created unique index on station 'code'.")

    # -----------------------------------------------------------------
    # STEP 3: Validate & Import Trains Collection
    # -----------------------------------------------------------------
    print("\n[3/4] Validating and Importing 'trains' collection...")
    trains_col = db["trains"]
    trains_col.drop()
    trains_col.create_index("trainNumber", unique=True)

    with open(trains_path, "r", encoding="utf-8") as f:
        trains_data = json.load(f)

    trains_with_missing_references = 0
    missing_reports = []

    print(f"  Validating station references across {len(trains_data):,} trains...")
    for train in trains_data:
        train_num = train.get("trainNumber", "UNKNOWN")
        train_name = train.get("trainName", "UNKNOWN")
        route = train.get("completeOrderedRoute", [])

        missing_codes_in_train = set()
        for stop in route:
            st_code = stop.get("stationCode")
            if st_code and st_code not in valid_station_codes:
                missing_codes_in_train.add(st_code)

        if missing_codes_in_train:
            trains_with_missing_references += 1
            missing_reports.append(
                f"Train #{train_num} ({train_name}) references missing station code(s): {', '.join(sorted(missing_codes_in_train))}"
            )

    # Write report file
    report_file_path = os.path.abspath(REPORT_FILENAME)
    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write("=== MISSING STATIONS REPORT ===\n")
        f.write(f"Total trains referencing missing stations: {trains_with_missing_references:,}\n\n")
        for line in missing_reports:
            f.write(line + "\n")

    print("[OK] Missing station validation complete.")
    print(f"  Logged {trains_with_missing_references:,} trains with missing station references to '{REPORT_FILENAME}'.")

    # Insert trains in batch chunks
    batch_size = 5000
    total_trains_inserted = 0
    for i in range(0, len(trains_data), batch_size):
        chunk = trains_data[i : i + batch_size]
        trains_col.insert_many(chunk)
        total_trains_inserted += len(chunk)

    print(f"[OK] Inserted {total_trains_inserted:,} train documents into 'trains' collection.")
    print("[OK] Created unique index on 'trainNumber'.")

    # -----------------------------------------------------------------
    # STEP 4: Bulk Import Delay History Collection with Error Handling
    # -----------------------------------------------------------------
    print("\n[4/4] Bulk importing 'delay_history' collection from CSV...")
    delay_col = db["delay_history"]
    delay_col.drop()

    chunksize = 100000
    total_csv_rows_read = 0
    total_delay_inserted = 0
    total_delay_failed = 0
    error_type_counts = defaultdict(int)

    start_time = time.time()
    chunk_index = 1

    print(f"  Reading '{os.path.basename(csv_path)}' in chunks of {chunksize:,} rows...")
    for chunk_df in pd.read_csv(csv_path, chunksize=chunksize):
        chunk_rows = len(chunk_df)
        total_csv_rows_read += chunk_rows

        # Convert NaN to None for MongoDB compatibility
        chunk_df = chunk_df.where(pd.notnull(chunk_df), None)
        records = chunk_df.to_dict("records")

        try:
            res = delay_col.insert_many(records, ordered=False)
            inserted = len(res.inserted_ids)
            total_delay_inserted += inserted
            print(f"    -> Chunk #{chunk_index:02d}: Inserted {inserted:,} rows (Total inserted: {total_delay_inserted:,})")

        except BulkWriteError as bwe:
            details = bwe.details
            inserted = details.get("nInserted", 0)
            write_errors = details.get("writeErrors", [])
            failed = len(write_errors)

            total_delay_inserted += inserted
            total_delay_failed += failed

            print(f"    -> Chunk #{chunk_index:02d}: BulkWriteError! {inserted:,} succeeded, {failed:,} failed.")

            # Print first 3 error reasons for this chunk
            print("       First 3 error samples:")
            for err in write_errors[:3]:
                err_code = err.get("code", "N/A")
                errmsg = err.get("errmsg", "Unknown error")
                print(f"         - [Code {err_code}] {errmsg}")

            # Categorize error types for summary report
            for err in write_errors:
                errmsg = err.get("errmsg", "Unknown error")
                if "duplicate key" in errmsg.lower():
                    err_type = "Duplicate Key Error (E11000)"
                elif "document too large" in errmsg.lower():
                    err_type = "BSON Document Size Limit Exceeded"
                else:
                    err_type = errmsg.split(":")[0] if ":" in errmsg else errmsg[:60]

                error_type_counts[err_type] += 1

        except Exception as e:
            print(f"    -> Chunk #{chunk_index:02d}: Unexpected Error: {e}")
            failed = len(records)
            total_delay_failed += failed
            error_type_counts[f"Unexpected: {type(e).__name__}"] += failed

        chunk_index += 1

    elapsed_sec = time.time() - start_time
    print(f"\n[OK] Processed {total_csv_rows_read:,} CSV rows in {elapsed_sec:.2f} seconds.")

    # -----------------------------------------------------------------
    # SUMMARY REPORT
    # -----------------------------------------------------------------
    print("\n=================================================================")
    print("                 IMPORT SUMMARY REPORT")
    print("=================================================================")
    print(f" Total Stations Inserted           : {total_stations_inserted:,}")
    print(f" Total Trains Inserted             : {total_trains_inserted:,}")
    print(f" Trains with Missing Stations      : {trains_with_missing_references:,}")
    print(f" Missing Stations Report Saved To  : {report_file_path}")
    print("-----------------------------------------------------------------")
    print(" DELAY HISTORY CSV BREAKDOWN:")
    print(f" Total CSV Rows Read               : {total_csv_rows_read:,}")
    print(f" Total Successfully Inserted       : {total_delay_inserted:,}")
    print(f" Total Failed Inserts              : {total_delay_failed:,}")
    if error_type_counts:
        print(" Failure Reasons Grouped by Error Type:")
        for err_type, count in error_type_counts.items():
            print(f"   - {err_type}: {count:,}")
    else:
        print(" Failure Reasons Grouped by Error Type: None (0 failures)")
    print("=================================================================\n")


if __name__ == "__main__":
    main()
