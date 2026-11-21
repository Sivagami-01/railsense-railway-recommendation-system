"""
Train Recommendation Engine Module
------------------------------------
Provides a 3-level hierarchical recommendation system for delayed train journeys,
combining route search (direct and multi-hop) with mock seat availability and
exact ISO datetime arithmetic.

Decision Logic:
1. Parse scheduled_time as ISO datetime (e.g., "2026-11-15T06:30:00").
2. Calculate delayed_arrival_dt = scheduled_dt + timedelta(minutes=delay_minutes).
3. If delay_minutes <= wait_tolerance_minutes: return "continue_with_booked_train".
4. Real-world catch check: Enforce candidate departure_dt >= now_dt + 10 mins (wall-clock guard).
5. Search direct trains arriving strictly between scheduled_dt and delayed_arrival_dt.
6. Classify direct trains into Level 1 (Express/Superfast/Premium) vs Level 2 (Local/Passenger/DEMU/MEMU).
7. Attach seat availability per class; discard options with 0 available seats across all classes.
8. Return Level 1 alternatives if any survive.
9. Else return Level 2 alternatives if any survive.
10. Else search 2-leg multi-hop trains (Level 3), enforcing min_layover_minutes (default 30 mins).
11. Return "no_alternative_available" if no options survive.
"""

from datetime import datetime, timedelta, time as datetime_time
import json
import re
import sys
from typing import Any, Dict, List, Optional
from pymongo import MongoClient

from route_search import (
    find_direct_trains,
    find_multi_hop_trains,
    parse_time_to_minutes,
)
from seat_availability import generate_seat_availability

# Configure stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# -----------------------------------------------------------------
# TRAIN TYPE CLASSIFICATION LISTS (EXHAUSTIVE MAP FOR ALL MONGODB TYPES)
# -----------------------------------------------------------------
LEVEL2_TRAIN_TYPES = {
    "DEMU", "MEMU", "PASS", "PASSENGER", "LOCAL", "COMMUTER", "TOY"
}

LEVEL1_TRAIN_TYPES = {
    "EXP", "EXPRESS", "SF", "SUPERFAST", "MAIL", "SKR", "SAMPARK KRANTI",
    "RAJ", "RAJDHANI", "DRNT", "DURONTO", "SHTB", "SHATABDI", "JSHTB",
    "JAN SHATABDI", "GR", "GARIB RATH", "VANDE BHARAT", "VB", "HUMSAFAR",
    "INTERCITY", "DEL", "HYD", "KLKT"
}

# Minimum buffer time in minutes required for traveler to catch alternative train
CATCH_BUFFER_MINUTES = 10
# Reasonable maximum wait before a transfer is considered unrealistic for a delayed trip
MAX_REASONABLE_WAIT_MINUTES = 180

STATION_ALIASES = {
    "MGR CHENNAI CENTRAL": "MAS",
    "CHENNAI CENTRAL": "MAS",
    "CHENNAI EGMORE": "MS",
    "CHENNAI BEACH": "MSB",
    "CHENNAI BEACH JN": "MSB",
}


def normalize_station_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def resolve_station_code(raw_station: str, db: Any) -> str:
    value = str(raw_station or "").strip()
    if not value:
        return ""

    normalized = normalize_station_token(value)
    alias_match = next(
        (
            code
            for station_name, code in STATION_ALIASES.items()
            if normalize_station_token(station_name) == normalized
        ),
        None,
    )
    if alias_match:
        return alias_match

    direct_code = db.stations.find_one({"code": value.upper()})
    if direct_code:
        return str(direct_code.get("code", "")).upper()

    for station in db.stations.find({}, {"code": 1, "name": 1}):
        if normalize_station_token(station.get("name", "")) == normalized:
            return str(station.get("code", "")).upper()

    return value.upper()


def parse_iso_or_time_str(dt_input: str) -> datetime:
    """
    Parses an ISO datetime string ("2026-11-15T06:30:00") or bare time string ("06:30:00").
    Defaults to today's date if only time is provided.
    """
    s = str(dt_input).strip()
    if "T" in s or "-" in s or " " in s:
        return datetime.fromisoformat(s.replace("Z", ""))
    else:
        parts = [int(p) for p in s.split(":")]
        t = datetime_time(parts[0], parts[1], parts[2] if len(parts) > 2 else 0)
        return datetime.combine(datetime.now().date(), t)


def is_level2_train(train_type: str) -> bool:
    """
    Determines whether a train_type belongs to local/passenger/DEMU/MEMU services (Level 2).
    """
    t = str(train_type).strip().upper()
    if t in LEVEL2_TRAIN_TYPES:
        return True
    return any(kw in t for kw in ["DEMU", "MEMU", "PASS", "LOCAL", "COMMUTER", "TOY"])


def normalize_train_number(raw_number: Optional[str]) -> str:
    if raw_number is None:
        return ""
    return str(raw_number).strip().lstrip("0")


def get_recommendations(
    source_code: str,
    destination_code: str,
    scheduled_time: str,
    delay_minutes: int,
    wait_tolerance_minutes: int,
    db: Any,
    current_time: Optional[str] = None,
    min_layover_minutes: int = 30,
    booked_train_number: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Computes alternative train recommendations for a delayed train journey using a
    3-level hierarchical policy with exact ISO datetime arithmetic, minimum layover guard,
    and wall-clock departure feasibility check.

    Args:
        source_code: Station code of origin (e.g. "JAT", "SSA").
        destination_code: Station code of destination (e.g. "UHP", "DNA").
        scheduled_time: Scheduled arrival time as ISO datetime string (e.g. "2026-11-15T06:30:00").
        delay_minutes: Expected delay in minutes of booked train.
        wait_tolerance_minutes: User's maximum acceptable delay tolerance in minutes.
        db: PyMongo database instance connected to "train_recommendation_system".
        current_time: Optional current wall-clock datetime string. Defaults to actual system datetime.
        min_layover_minutes: Minimum connection buffer in minutes for Level 3 transfers (default 30 mins).

    Returns:
        Dict[str, Any]: Recommendation decision output dictionary.
    """
    src = resolve_station_code(source_code, db).upper()
    dst = resolve_station_code(destination_code, db).upper()

    # Step 1: Parse scheduled_time, current_time, and compute delayed_arrival_dt
    scheduled_dt = parse_iso_or_time_str(scheduled_time)
    delayed_arrival_dt = scheduled_dt + timedelta(minutes=delay_minutes)
    delayed_arrival_time_str = delayed_arrival_dt.isoformat()

    if current_time:
        now_dt = parse_iso_or_time_str(current_time)
    else:
        now_dt = datetime.now()

    # Step 2: Immediate return if delay is within user wait tolerance
    if delay_minutes <= wait_tolerance_minutes:
        return {
            "decision": "continue_with_booked_train",
            "reason": (
                f"Expected delay of {delay_minutes} minutes is within user wait "
                f"tolerance of {wait_tolerance_minutes} minutes."
            ),
            "delayed_arrival_time": delayed_arrival_time_str,
            "alternatives": [],
        }

    # Step 3: Search Direct Trains
    direct_candidates = find_direct_trains(src, dst, db)

    level1_options: List[Dict[str, Any]] = []
    level2_options: List[Dict[str, Any]] = []
    booked_train_key = normalize_train_number(booked_train_number)

    for cand in direct_candidates:
        candidate_number = str(cand.get("trainNumber", "")).strip()
        if booked_train_key and normalize_train_number(candidate_number) == booked_train_key:
            continue

        dep_time_str = cand.get("departureTimeAtSource")
        dur_mins = cand.get("durationMinutes", 0)

        if not dep_time_str:
            continue

        parts = [int(p) for p in dep_time_str.split(":")]
        cand_dep_t = datetime_time(parts[0], parts[1], parts[2] if len(parts) > 2 else 0)

        # Exact Datetime arithmetic across candidate departure days [-1, 0, 1]
        valid_arrival_dt = None
        for day_offset in [-1, 0, 1]:
            dep_dt = datetime.combine(scheduled_dt.date() + timedelta(days=day_offset), cand_dep_t)
            arr_dt = dep_dt + timedelta(minutes=dur_mins)
            wait_minutes = int((dep_dt - scheduled_dt).total_seconds() // 60)

            # Reject unrealistic waits (e.g. 7-8 hour station waits after a delay)
            if wait_minutes > MAX_REASONABLE_WAIT_MINUTES:
                continue

            # Check 1: Arrival strictly between scheduled_dt and delayed_arrival_dt
            # Check 2: Departure is in the future relative to current wall-clock time (+ buffer)
            if (scheduled_dt < arr_dt < delayed_arrival_dt) and (dep_dt >= now_dt + timedelta(minutes=CATCH_BUFFER_MINUTES)):
                valid_arrival_dt = arr_dt
                break

        if valid_arrival_dt is None:
            continue

        # Attach seat availability and discard option if all classes show 0 seats
        seat_avail = generate_seat_availability(cand.get("type", "Mail/Express"), None)
        if not seat_avail or max(seat_avail.values(), default=0) <= 0:
            continue

        sub_route = cand.get("subRoute", [])
        station_seq = [
            str(s.get("stationCode")).upper()
            for s in sub_route
            if s.get("stationCode")
        ]

        is_lvl2 = is_level2_train(cand.get("type", ""))
        lvl = 2 if is_lvl2 else 1

        formatted_option = {
            "trainNumber": cand.get("trainNumber"),
            "trainName": cand.get("trainName"),
            "type": cand.get("type"),
            "level": lvl,
            "departureTime": cand.get("departureTimeAtSource"),
            "arrivalTime": cand.get("arrivalTimeAtDestination"),
            "durationMinutes": cand.get("durationMinutes"),
            "stationSequence": station_seq,
            "seatAvailability": seat_avail,
        }

        if is_lvl2:
            level2_options.append(formatted_option)
        else:
            level1_options.append(formatted_option)

    # Return Level 1 options if available
    if level1_options:
        level1_options.sort(key=lambda x: x["durationMinutes"])
        return {
            "decision": "alternative_found",
            "level": 1,
            "delayed_arrival_time": delayed_arrival_time_str,
            "alternatives": level1_options,
        }

    # Return Level 2 options if available
    if level2_options:
        level2_options.sort(key=lambda x: x["durationMinutes"])
        return {
            "decision": "alternative_found",
            "level": 2,
            "delayed_arrival_time": delayed_arrival_time_str,
            "alternatives": level2_options,
        }

    # Step 8: Multi-hop Search (Level 3)
    multi_candidates = find_multi_hop_trains(
        src,
        dst,
        db,
        max_hops=2,
        min_layover_minutes=min_layover_minutes,
        max_layover_minutes=MAX_REASONABLE_WAIT_MINUTES,
        compare_to_direct_duration=None,
    )

    level3_options: List[Dict[str, Any]] = []

    for multi in multi_candidates:
        leg1 = multi.get("leg1", {})
        leg2 = multi.get("leg2", {})

        leg1_number = str(leg1.get("trainNumber", "")).strip()
        leg2_number = str(leg2.get("trainNumber", "")).strip()
        if booked_train_key and (
            normalize_train_number(leg1_number) == booked_train_key
            or normalize_train_number(leg2_number) == booked_train_key
        ):
            continue

        leg1_dep_str = leg1.get("departureTime")
        total_dur_mins = multi.get("totalJourneyMinutes", 0)

        if not leg1_dep_str:
            continue

        parts = [int(p) for p in leg1_dep_str.split(":")]
        leg1_dep_t = datetime_time(parts[0], parts[1], parts[2] if len(parts) > 2 else 0)

        # Exact Datetime arithmetic for Multi-hop combos
        valid_arrival_dt = None
        for day_offset in [-1, 0, 1]:
            dep_dt = datetime.combine(scheduled_dt.date() + timedelta(days=day_offset), leg1_dep_t)
            arr_dt = dep_dt + timedelta(minutes=total_dur_mins)
            wait_minutes = int((dep_dt - scheduled_dt).total_seconds() // 60)

            if wait_minutes > MAX_REASONABLE_WAIT_MINUTES:
                continue

            # Check 1: Arrival strictly between scheduled_dt and delayed_arrival_dt
            # Check 2: Departure is in the future relative to current wall-clock time (+ buffer)
            if (scheduled_dt < arr_dt < delayed_arrival_dt) and (dep_dt >= now_dt + timedelta(minutes=CATCH_BUFFER_MINUTES)):
                valid_arrival_dt = arr_dt
                break

        if valid_arrival_dt is None:
            continue

        # Attach seat availability to both legs
        leg1_seats = generate_seat_availability(leg1.get("type", "Mail/Express"), None)
        leg2_seats = generate_seat_availability(leg2.get("type", "Mail/Express"), None)

        if not leg1_seats or max(leg1_seats.values(), default=0) <= 0:
            continue
        if not leg2_seats or max(leg2_seats.values(), default=0) <= 0:
            continue

        leg1_seq = [
            str(s.get("stationCode")).upper()
            for s in leg1.get("subRoute", [])
            if s.get("stationCode")
        ]
        leg2_seq = [
            str(s.get("stationCode")).upper()
            for s in leg2.get("subRoute", [])
            if s.get("stationCode")
        ]

        formatted_combo = {
            "leg1": {
                "trainNumber": leg1.get("trainNumber"),
                "trainName": leg1.get("trainName"),
                "type": leg1.get("type"),
                "departureTime": leg1.get("departureTime"),
                "arrivalTime": leg1.get("arrivalTime"),
                "durationMinutes": leg1.get("durationMinutes"),
                "stationSequence": leg1_seq,
                "seatAvailability": leg1_seats,
            },
            "leg2": {
                "trainNumber": leg2.get("trainNumber"),
                "trainName": leg2.get("trainName"),
                "type": leg2.get("type"),
                "departureTime": leg2.get("departureTime"),
                "arrivalTime": leg2.get("arrivalTime"),
                "durationMinutes": leg2.get("durationMinutes"),
                "stationSequence": leg2_seq,
                "seatAvailability": leg2_seats,
            },
            "transferStation": multi.get("transferStation"),
            "layoverMinutes": multi.get("layoverMinutes"),
            "totalDurationMinutes": multi.get("totalJourneyMinutes"),
        }

        level3_options.append(formatted_combo)

    if level3_options:
        level3_options.sort(key=lambda x: x["totalDurationMinutes"])
        return {
            "decision": "alternative_found",
            "level": 3,
            "delayed_arrival_time": delayed_arrival_time_str,
            "alternatives": level3_options,
        }

    # Step 9: No alternative found
    return {
        "decision": "no_alternative_available",
        "delayed_arrival_time": delayed_arrival_time_str,
        "alternatives": [],
        "reason": "No valid alternative found within the delay window.",
    }


if __name__ == "__main__":
    client = MongoClient("mongodb://localhost:27017")
    db = client["train_recommendation_system"]

    print("=================================================================")
    print("   INDIAN RAILWAYS ALTERNATIVE TRAIN RECOMMENDATION ENGINE DEMO  ")
    print("=================================================================")

    print("\n--- TEST SCENARIO 1: Level 1 Express Winner (JAT -> UHP) ---")
    res1 = get_recommendations(
        source_code="JAT",
        destination_code="UHP",
        scheduled_time="2026-11-15T06:30:00",
        delay_minutes=120,
        wait_tolerance_minutes=30,
        db=db,
    )
    print(json.dumps(res1, indent=2))
