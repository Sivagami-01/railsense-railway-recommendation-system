"""
Alternative Train Recommendation Engine Module
------------------------------------------------
Provides a 3-level hierarchical recommendation system for delayed train journeys.

Hierarchy:
  - Level 1: Direct Express / Superfast / Premium Trains
  - Level 2: Direct Local / Passenger / DEMU / MEMU Trains
  - Level 3: Multi-hop (1-transfer) Progressive Route Combinations

Filters candidates by departure time (> current_time), day-aware arrival window
(strictly between scheduled_time and delayed_arrival_time), and seat availability.

Uses PyMongo and Python Standard Library (json, math, sys, typing).
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple
from pymongo import MongoClient

# Ensure local imports from workspace work seamlessly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from route_search import (
    calculate_total_duration,
    find_direct_trains,
    find_multi_hop_trains,
    parse_time_to_minutes,
)
from seat_availability import generate_seat_availability

# Configure stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def add_minutes_to_time(time_str: str, minutes_to_add: int) -> str:
    """
    Adds a specified number of minutes to an HH:MM:SS or HH:MM time string.

    Args:
        time_str: Initial time string (e.g. "13:00:00").
        minutes_to_add: Number of minutes to add (e.g. 120).

    Returns:
        str: Resulting time string in "HH:MM:SS" format.
    """
    base_mins = parse_time_to_minutes(time_str)
    if base_mins is None:
        return time_str

    total_mins = base_mins + minutes_to_add
    wrapped_mins = total_mins % (24 * 60)
    hrs = wrapped_mins // 60
    mins = wrapped_mins % 60
    secs = 0
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


def is_local_passenger_type(train_type: str) -> bool:
    """
    Determines whether a train_type belongs to local/passenger/DEMU/MEMU services (Level 2).

    Args:
        train_type: String train type (e.g. "SUPERFAST", "DEMU", "Passenger Train").

    Returns:
        bool: True if local/passenger type, False if express/premium (Level 1).
    """
    t = str(train_type).strip().upper()
    level2_types = {"DEMU", "MEMU", "PASS", "PASSENGER", "LOCAL", "COMMUTER", "TOY"}
    return t in level2_types or any(kw in t for kw in ["DEMU", "MEMU", "PASS", "LOCAL"])


def recommend_alternatives(
    source_code: str,
    destination_code: str,
    scheduled_time: str,
    delay_minutes: int,
    wait_tolerance_minutes: int,
    current_time: str,
    db: Any,
) -> Dict[str, Any]:
    """
    Recommends alternative train options using a 3-level hierarchical selection policy.

    Args:
        source_code: Origin station code (e.g. "TPJ" or "JAT").
        destination_code: Destination station code (e.g. "MS" or "UHP").
        scheduled_time: Scheduled arrival time at destination ("HH:MM:SS").
        delay_minutes: Expected delay in minutes of booked train.
        wait_tolerance_minutes: User's maximum acceptable delay tolerance in minutes.
        current_time: Current time when user checks ("HH:MM:SS").
        db: PyMongo database instance.

    Returns:
        Dict[str, Any]: Structured recommendation result dictionary.
    """
    src = source_code.strip().upper()
    dst = destination_code.strip().upper()

    # Compute delayed arrival time string
    delayed_arrival_time = add_minutes_to_time(scheduled_time, delay_minutes)

    # Decision Rule 1: If delay is within user tolerance, stick with booked train
    if delay_minutes <= wait_tolerance_minutes:
        return {
            "decision": "continue_with_booked_train",
            "level": None,
            "delayed_arrival_time": delayed_arrival_time,
            "alternatives": [],
        }

    # -----------------------------------------------------------------
    # DAY-AWARE MINUTE-BASED TIMING ARITHMETIC:
    # Convert all timing bounds into total minutes from departure Day 1 00:00.
    # -----------------------------------------------------------------
    current_mins = parse_time_to_minutes(current_time) or 0
    sched_mins = parse_time_to_minutes(scheduled_time) or 0

    if sched_mins < current_mins:
        sched_arr_mins_total = sched_mins + 1440
    else:
        sched_arr_mins_total = sched_mins

    delayed_arr_mins_total = sched_arr_mins_total + delay_minutes

    # 1. Search Direct Trains
    direct_candidates = find_direct_trains(src, dst, db)

    level1_options: List[Dict[str, Any]] = []
    level2_options: List[Dict[str, Any]] = []

    for cand in direct_candidates:
        dep_mins = parse_time_to_minutes(cand["departureTimeAtSource"])
        arr_mins = parse_time_to_minutes(cand["arrivalTimeAtDestination"])

        if dep_mins is None or arr_mins is None:
            continue

        cand_arr_mins_total = dep_mins + cand["durationMinutes"]

        # Condition A: Departure from source must be strictly AFTER current_time
        if dep_mins <= current_mins:
            continue

        # Condition B: Arrival at destination strictly between scheduled_time and delayed_arrival_time
        if not (sched_arr_mins_total < cand_arr_mins_total < delayed_arr_mins_total):
            continue

        # Condition C: Generate seat availability and check eligibility (>0 seats in at least 1 class)
        seat_avail = generate_seat_availability(cand["type"])
        max_seats = max(seat_avail.values()) if seat_avail else 0
        if max_seats <= 0:
            continue

        formatted_option = {
            "trainNumber": cand["trainNumber"],
            "trainName": cand["trainName"],
            "type": cand["type"],
            "departureTime": cand["departureTimeAtSource"],
            "arrivalTime": cand["arrivalTimeAtDestination"],
            "durationMinutes": cand["durationMinutes"],
            "journeyDaySpan": cand["journeyDaySpan"],
            "seatAvailability": seat_avail,
            "routePath": [s["stationCode"] for s in cand["subRoute"]],
        }

        if is_local_passenger_type(cand["type"]):
            level2_options.append(formatted_option)
        else:
            level1_options.append(formatted_option)

    # 2. Search Multi-Hop Trains
    level3_options: List[Dict[str, Any]] = []

    direct_cap = (
        min(c["durationMinutes"] for c in (level1_options + level2_options))
        if (level1_options or level2_options)
        else None
    )

    multi_candidates = find_multi_hop_trains(
        src, dst, db, max_hops=2, compare_to_direct_duration=direct_cap
    )

    for multi in multi_candidates:
        leg1 = multi["leg1"]
        leg2 = multi["leg2"]

        dep_mins = parse_time_to_minutes(leg1["departureTime"])
        arr_mins = parse_time_to_minutes(leg2["arrivalTime"])

        if dep_mins is None or arr_mins is None:
            continue

        multi_arr_mins_total = dep_mins + multi["totalJourneyMinutes"]

        # Condition A: Departure from source must be strictly AFTER current_time
        if dep_mins <= current_mins:
            continue

        # Condition B: Arrival at destination strictly between scheduled_time and delayed_arrival_time
        if not (sched_arr_mins_total < multi_arr_mins_total < delayed_arr_mins_total):
            continue

        # Condition C: Seat availability across both legs (Intersection & Per-Class Minimum Bottleneck)
        avail_leg1 = generate_seat_availability(leg1["type"])
        avail_leg2 = generate_seat_availability(leg2["type"])

        # Include ONLY classes present in BOTH legs, taking min(leg1, leg2)
        common_classes = set(avail_leg1.keys()).intersection(set(avail_leg2.keys()))
        combined_avail: Dict[str, int] = {
            cls: min(avail_leg1[cls], avail_leg2[cls]) for cls in common_classes
        }

        # Require at least 1 common class with >= 1 seat available across BOTH legs
        if max(combined_avail.values(), default=0) <= 0:
            continue

        level3_options.append(
            {
                "leg1": {
                    "trainNumber": leg1["trainNumber"],
                    "trainName": leg1["trainName"],
                    "type": leg1["type"],
                    "departureTime": leg1["departureTime"],
                    "arrivalTime": leg1["arrivalTime"],
                    "seatAvailability": avail_leg1,
                },
                "leg2": {
                    "trainNumber": leg2["trainNumber"],
                    "trainName": leg2["trainName"],
                    "type": leg2["type"],
                    "departureTime": leg2["departureTime"],
                    "arrivalTime": leg2["arrivalTime"],
                    "seatAvailability": avail_leg2,
                },
                "transferStation": multi["transferStation"],
                "layoverMinutes": multi["layoverMinutes"],
                "totalDurationMinutes": multi["totalJourneyMinutes"],
                "seatAvailability": combined_avail,
                "routePath": [s["stationCode"] for s in multi["combinedRoute"]],
            }
        )

    # -----------------------------------------------------------------
    # HIERARCHICAL LEVEL SELECTION POLICY (Level 1 > Level 2 > Level 3)
    # -----------------------------------------------------------------
    if level1_options:
        level1_options.sort(key=lambda x: parse_time_to_minutes(x["arrivalTime"]) or 0)
        return {
            "decision": "alternatives_found",
            "level": 1,
            "delayed_arrival_time": delayed_arrival_time,
            "alternatives": level1_options,
        }
    elif level2_options:
        level2_options.sort(key=lambda x: parse_time_to_minutes(x["arrivalTime"]) or 0)
        return {
            "decision": "alternatives_found",
            "level": 2,
            "delayed_arrival_time": delayed_arrival_time,
            "alternatives": level2_options,
        }
    elif level3_options:
        level3_options.sort(key=lambda x: x["totalDurationMinutes"])
        return {
            "decision": "alternatives_found",
            "level": 3,
            "delayed_arrival_time": delayed_arrival_time,
            "alternatives": level3_options,
        }
    else:
        return {
            "decision": "no_alternatives_found",
            "level": None,
            "delayed_arrival_time": delayed_arrival_time,
            "alternatives": [],
        }


if __name__ == "__main__":
    print("=================================================================")
    print("      TRAIN RECOMMENDATION ENGINE - COMPREHENSIVE SUITE")
    print("=================================================================")

    client = MongoClient("mongodb://localhost:27017")
    db = client["train_recommendation_system"]

    print("\n--- DAY-AWARE MINUTE ARITHMETIC VERIFICATION CODE SNIPPET ---")
    print("""
    current_mins = parse_time_to_minutes(current_time)
    sched_mins = parse_time_to_minutes(scheduled_time)
    
    if sched_mins < current_mins:
        sched_arr_mins_total = sched_mins + 1440  # Next calendar day
    else:
        sched_arr_mins_total = sched_mins
        
    delayed_arr_mins_total = sched_arr_mins_total + delay_minutes
    cand_arr_mins_total = dep_mins + candidate_duration_minutes

    is_eligible = (current_mins < dep_mins) and (sched_arr_mins_total < cand_arr_mins_total < delayed_arr_mins_total)
    """)
    print("-----------------------------------------------------------------")

    # -------------------------------------------------------------------
    # TEST 1: User Prompt Request Parameters (TPJ -> MS, scheduled 13:00, delay 120m)
    # -------------------------------------------------------------------
    print("\n[TEST 1] User Prompt Parameters (TPJ -> MS, 120m delay, current 12:30:00):")
    res1 = recommend_alternatives("TPJ", "MS", "13:00:00", 120, 15, "12:30:00", db)
    print(f"  Decision: {res1['decision']} | Level: {res1['level']} | Delayed Arrival: {res1['delayed_arrival_time']}")
    print(json.dumps(res1, indent=2))

    # -------------------------------------------------------------------
    # TEST 2: Level 1 Selection (TPJ -> MS, Express / Superfast Trains)
    # -------------------------------------------------------------------
    print("\n-----------------------------------------------------------------")
    print("[TEST 2] Validation of LEVEL 1 Selection (TPJ -> MS, Express Trains):")
    print("  Scheduled: 21:00:00 | Delay: 180m -> Delayed Arrival: 00:00:00 (CROSSES MIDNIGHT!)")
    res2 = recommend_alternatives("TPJ", "MS", "21:00:00", 180, 15, "13:00:00", db)
    print(f"  Decision: {res2['decision']} | Level: {res2['level']} | Delayed Arrival: {res2['delayed_arrival_time']}")
    print(json.dumps(res2, indent=2))

    # -------------------------------------------------------------------
    # TEST 3: Level 2 Selection (SSA -> HSR, Direct Passenger Train #04741)
    # -------------------------------------------------------------------
    print("\n-----------------------------------------------------------------")
    print("[TEST 3] Validation of LEVEL 2 Selection (SSA -> HSR, Passenger Train):")
    print("  Scheduled: 23:50:00 | Delay: 40m -> Delayed Arrival: 00:30:00 (CROSSES MIDNIGHT!)")
    res3 = recommend_alternatives("SSA", "HSR", "23:50:00", 40, 15, "22:00:00", db)
    print(f"  Decision: {res3['decision']} | Level: {res3['level']} | Delayed Arrival: {res3['delayed_arrival_time']}")
    print(json.dumps(res3, indent=2))

    # -------------------------------------------------------------------
    # TEST 4: Level 3 Selection & Per-Class Minimum Bottleneck Validation (SSA -> DNA)
    # -------------------------------------------------------------------
    print("\n-----------------------------------------------------------------")
    print("[TEST 4] Validation of LEVEL 3 Selection & Per-Class Minimum Seats (SSA -> DNA):")
    print("  Scheduled: 09:00:00 | Delay: 240m -> Delayed Arrival: 13:00:00 (CROSSES MIDNIGHT!)")
    res4 = recommend_alternatives("SSA", "DNA", "09:00:00", 240, 15, "22:00:00", db)
    print(f"  Decision: {res4['decision']} | Level: {res4['level']} | Delayed Arrival: {res4['delayed_arrival_time']}")
    print(json.dumps(res4, indent=2))

    if res4["alternatives"]:
        alt = res4["alternatives"][0]
        l1_seats = alt["leg1"]["seatAvailability"]
        l2_seats = alt["leg2"]["seatAvailability"]
        combo_seats = alt["seatAvailability"]

        print("\n=== SIDE-BY-SIDE SEAT AVAILABILITY BOTTLENECK CHECK ===")
        print(f"{'Class':<8} | {'Leg 1 Seats':<12} | {'Leg 2 Seats':<12} | {'Combo Min Seats (Bottleneck)':<28}")
        print("-" * 65)
        for cls in sorted(combo_seats.keys()):
            s1 = l1_seats.get(cls, "N/A")
            s2 = l2_seats.get(cls, "N/A")
            cm = combo_seats.get(cls, "N/A")
            print(f"{cls:<8} | {s1:<12} | {s2:<12} | {cm:<28}")
        print("=" * 65)

    print("\n=================================================================")
