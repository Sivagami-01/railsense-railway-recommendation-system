"""
Train Route Search Module
-------------------------
Provides direct and multi-hop route finding across Indian Railways trains
stored in MongoDB ("train_recommendation_system").

Features:
  - Direct route search with direction and sub-route extraction
  - Multi-hop (1-transfer) route search with distance guard (Haversine formula)
  - Backtracking protection (discards combos where Leg 2 post-X stations overlap Leg 1)
  - Path deduplication, top-10 result capping, and direct-duration filtering

Uses PyMongo and Python Standard Library (math, sys, typing).
"""

import math
import sys
from typing import Any, Dict, List, Optional, Tuple
from pymongo import MongoClient

# Configure stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two geographic points in kilometers
    using the Haversine formula.

    Args:
        lat1, lon1: Latitude and longitude of point 1 in degrees.
        lat2, lon2: Latitude and longitude of point 2 in degrees.

    Returns:
        float: Distance in kilometers.
    """
    R = 6371.0  # Earth's mean radius in kilometers
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def get_station_coords(station_code: str, db: Any) -> Optional[Tuple[float, float]]:
    """
    Fetches the (latitude, longitude) coordinates for a station code from the 'stations' collection.

    Args:
        station_code: Station code (e.g. "JAT").
        db: PyMongo database instance.

    Returns:
        Optional[Tuple[float, float]]: (latitude, longitude) or None if missing/invalid.
    """
    station = db.stations.find_one({"code": station_code.strip().upper()})
    if station and "coordinates" in station and isinstance(station["coordinates"], dict):
        coords = station["coordinates"]
        lat = coords.get("latitude", 0.0)
        lon = coords.get("longitude", 0.0)
        if lat != 0 and lon != 0:
            return (float(lat), float(lon))
    return None


def parse_time_to_minutes(time_str: Optional[str]) -> Optional[int]:
    """
    Parses a time string ("HH:MM:SS" or "HH:MM") into total minutes from midnight.

    Args:
        time_str: Time string (e.g., "10:40:00" or "10:40").

    Returns:
        Optional[int]: Total minutes from 00:00, or None if invalid/missing.
    """
    if not time_str:
        return None
    try:
        parts = [int(p) for p in str(time_str).strip().split(":")]
        if len(parts) >= 2:
            return parts[0] * 60 + parts[1]
    except Exception:
        pass
    return None


def calculate_total_duration(
    departure_time: str,
    arrival_time: str,
    journey_day_start: int = 1,
    journey_day_end: int = 1,
) -> int:
    """
    Calculates total journey duration in minutes between departure and arrival,
    correctly handling multi-day journeys using journey_day_start and journey_day_end.

    Args:
        departure_time: Departure time string at source station.
        arrival_time: Arrival time string at destination station.
        journey_day_start: Journey day index at source (1-based, default 1).
        journey_day_end: Journey day index at destination (1-based, default 1).

    Returns:
        int: Total duration in minutes (minimum 0).
    """
    dep_mins = parse_time_to_minutes(departure_time)
    arr_mins = parse_time_to_minutes(arrival_time)

    if dep_mins is None or arr_mins is None:
        return 0

    day_diff = max(0, journey_day_end - journey_day_start)
    total_minutes = (day_diff * 24 * 60) + (arr_mins - dep_mins)

    if total_minutes < 0:
        total_minutes += 24 * 60

    return max(0, total_minutes)


def find_direct_trains(
    source_code: str, destination_code: str, db: Any
) -> List[Dict[str, Any]]:
    """
    Searches the "trains" collection for trains operating directly from source_code to destination_code.

    Args:
        source_code: Origin station code.
        destination_code: Destination station code.
        db: PyMongo database instance.

    Returns:
        List[Dict[str, Any]]: List of matching direct train dictionaries containing subRoute and timing stats.
    """
    src = source_code.strip().upper()
    dst = destination_code.strip().upper()

    cursor = db.trains.find({"completeOrderedRoute.stationCode": src})
    direct_trains: List[Dict[str, Any]] = []

    for train in cursor:
        route = train.get("completeOrderedRoute", [])
        src_index = -1
        dst_index = -1

        for idx, stop in enumerate(route):
            code = str(stop.get("stationCode", "")).strip().upper()
            if code == src and src_index == -1:
                src_index = idx
            elif code == dst and src_index != -1 and dst_index == -1:
                dst_index = idx

        if src_index != -1 and dst_index != -1 and src_index < dst_index:
            sub_route_raw = route[src_index : dst_index + 1]
            src_stop = sub_route_raw[0]
            dst_stop = sub_route_raw[-1]

            dep_time = (
                src_stop.get("departureTime")
                or src_stop.get("arrivalTime")
                or "00:00:00"
            )
            arr_time = (
                dst_stop.get("arrivalTime")
                or dst_stop.get("departureTime")
                or "00:00:00"
            )

            day_start = src_stop.get("journeyDay", 1) or 1
            day_end = dst_stop.get("journeyDay", 1) or 1

            duration = calculate_total_duration(dep_time, arr_time, day_start, day_end)

            sub_route = [
                {
                    "sequence": stop.get("sequence"),
                    "stationCode": stop.get("stationCode"),
                    "stationName": stop.get("stationName"),
                    "arrivalTime": stop.get("arrivalTime"),
                    "departureTime": stop.get("departureTime"),
                    "journeyDay": stop.get("journeyDay"),
                    "distance": stop.get("distance"),
                }
                for stop in sub_route_raw
            ]

            direct_trains.append(
                {
                    "trainNumber": train.get("trainNumber"),
                    "trainName": train.get("trainName"),
                    "type": train.get("type"),
                    "runningDays": train.get("runningDays"),
                    "subRoute": sub_route,
                    "departureTimeAtSource": dep_time,
                    "arrivalTimeAtDestination": arr_time,
                    "journeyDaySpan": day_end - day_start,
                    "durationMinutes": duration,
                }
            )

    direct_trains.sort(key=lambda t: (t["journeyDaySpan"], t["durationMinutes"]))
    return direct_trains


def find_multi_hop_trains(
    source_code: str,
    destination_code: str,
    db: Any,
    max_hops: int = 2,
    min_layover_minutes: int = 30,
    max_layover_minutes: int = 180,
    compare_to_direct_duration: Optional[int] = None,
    return_stats: bool = False,
) -> Any:
    """
    Finds 2-leg transfer journeys (Source -> Intermediate Station X -> Destination).

    Args:
        source_code: Station code of origin station.
        destination_code: Station code of final destination station.
        db: PyMongo database instance.
        max_hops: Maximum number of train legs allowed (default 2).
        min_layover_minutes: Minimum layover buffer in minutes at transfer station (default 30 mins).
        compare_to_direct_duration: If provided, filters out any multi-hop option whose
                                   durationMinutes >= compare_to_direct_duration.
        return_stats: If True, returns tuple (results_list, stats_dict).

    Returns:
        List[Dict[str, Any]] (or Tuple if return_stats=True): Top 10 fastest multi-hop option dictionaries sorted by duration.
    """
    src = source_code.strip().upper()
    dst = destination_code.strip().upper()

    if max_hops < 2:
        return ([], {}) if return_stats else []

    # Fetch station coordinates for Haversine distance guard
    coords_src = get_station_coords(src, db)
    coords_dst = get_station_coords(dst, db)

    direct_geo_dist = None
    if coords_src and coords_dst:
        direct_geo_dist = haversine_distance(
            coords_src[0], coords_src[1], coords_dst[0], coords_dst[1]
        )

    # Step 1: Candidate Leg 1 trains passing through source_code
    trains_src = list(db.trains.find({"completeOrderedRoute.stationCode": src}))
    leg1_map: Dict[str, List[Dict[str, Any]]] = {}

    for train_a in trains_src:
        route_a = train_a.get("completeOrderedRoute", [])
        src_idx = next(
            (i for i, s in enumerate(route_a) if str(s.get("stationCode")).upper() == src),
            -1,
        )

        if src_idx != -1:
            for idx_a in range(src_idx + 1, len(route_a)):
                stop_x = route_a[idx_a]
                x_code = str(stop_x.get("stationCode")).upper()

                if x_code and x_code != dst:
                    # Apply Distance Guard for candidate transfer station X
                    if direct_geo_dist is not None:
                        coords_x = get_station_coords(x_code, db)
                        if coords_x:
                            dist_leg1_geo = haversine_distance(
                                coords_src[0], coords_src[1], coords_x[0], coords_x[1]
                            )
                            dist_leg2_geo = haversine_distance(
                                coords_x[0], coords_x[1], coords_dst[0], coords_dst[1]
                            )
                            total_estimated_dist = dist_leg1_geo + dist_leg2_geo

                            # Discard if combined travel distance > 1.5x straight-line distance
                            if total_estimated_dist > 1.5 * direct_geo_dist:
                                continue

                    sub_route_a = route_a[src_idx : idx_a + 1]
                    src_stop_a = sub_route_a[0]

                    dep_a = (
                        src_stop_a.get("departureTime")
                        or src_stop_a.get("arrivalTime")
                        or "00:00:00"
                    )
                    arr_x_a = (
                        stop_x.get("arrivalTime")
                        or stop_x.get("departureTime")
                        or "00:00:00"
                    )

                    day_start_a = src_stop_a.get("journeyDay", 1) or 1
                    day_end_a = stop_x.get("journeyDay", 1) or 1
                    dur_a = calculate_total_duration(dep_a, arr_x_a, day_start_a, day_end_a)

                    if x_code not in leg1_map:
                        leg1_map[x_code] = []

                    leg1_map[x_code].append(
                        {
                            "trainNumber": train_a.get("trainNumber"),
                            "trainName": train_a.get("trainName"),
                            "type": train_a.get("type"),
                            "runningDays": train_a.get("runningDays"),
                            "subRoute": sub_route_a,
                            "departureTime": dep_a,
                            "arrivalTime": arr_x_a,
                            "journeyDayStart": day_start_a,
                            "journeyDayEnd": day_end_a,
                            "durationMinutes": dur_a,
                            "transferStationName": stop_x.get("stationName"),
                        }
                    )

    # Step 2: Candidate Leg 2 trains passing through destination_code
    trains_dst = list(db.trains.find({"completeOrderedRoute.stationCode": dst}))
    raw_multi_hop_routes: List[Dict[str, Any]] = []

    candidates_before_backtrack = 0

    for train_b in trains_dst:
        route_b = train_b.get("completeOrderedRoute", [])
        dst_idx = next(
            (i for i, s in enumerate(route_b) if str(s.get("stationCode")).upper() == dst),
            -1,
        )

        if dst_idx != -1:
            for idx_b in range(0, dst_idx):
                stop_x = route_b[idx_b]
                x_code = str(stop_x.get("stationCode")).upper()

                if x_code in leg1_map:
                    sub_route_b = route_b[idx_b : dst_idx + 1]
                    dst_stop_b = sub_route_b[-1]

                    dep_x_b = (
                        stop_x.get("departureTime")
                        or stop_x.get("arrivalTime")
                        or "00:00:00"
                    )
                    arr_b = (
                        dst_stop_b.get("arrivalTime")
                        or dst_stop_b.get("departureTime")
                        or "00:00:00"
                    )

                    day_start_b = stop_x.get("journeyDay", 1) or 1
                    day_end_b = dst_stop_b.get("journeyDay", 1) or 1
                    dur_b = calculate_total_duration(dep_x_b, arr_b, day_start_b, day_end_b)

                    for leg1 in leg1_map[x_code]:
                        if leg1["trainNumber"] == train_b.get("trainNumber"):
                            continue  # Skip same train loop

                        arr_x_mins = parse_time_to_minutes(leg1["arrivalTime"])
                        dep_x_mins = parse_time_to_minutes(dep_x_b)

                        if arr_x_mins is not None and dep_x_mins is not None:
                            # Exact layover in minutes with midnight rollover
                            layover = (dep_x_mins - arr_x_mins) % 1440

                            # Discard tight transfers and absurd waits (e.g. 7-8 hour station waits)
                            if not (min_layover_minutes <= layover <= max_layover_minutes):
                                continue

                            candidates_before_backtrack += 1

                            # -------------------------------------------------------------
                            # STRICT BACKTRACKING FILTER:
                            # 1. Set of station codes in Leg 1's sub-route (source_code through X, inclusive)
                            # 2. Set of station codes in Leg 2's sub-route AFTER X (post-X stations through destination_code)
                            # 3. If Leg 2's post-X stations overlap ANY station in Leg 1, DISCARD as backtracking!
                            # -------------------------------------------------------------
                            leg1_station_set = {
                                str(s.get("stationCode")).upper()
                                for s in leg1["subRoute"]
                            }
                            leg2_post_x_set = {
                                str(s.get("stationCode")).upper()
                                for s in sub_route_b[1:]
                            }

                            if leg1_station_set.intersection(leg2_post_x_set):
                                continue  # Discard backtracking combo

                            total_journey_mins = (
                                leg1["durationMinutes"] + layover + dur_b
                            )

                            # Filter out options slower than or equal to direct train duration if provided
                            if (
                                compare_to_direct_duration is not None
                                and total_journey_mins >= compare_to_direct_duration
                            ):
                                continue

                            combined_route = list(leg1["subRoute"]) + list(sub_route_b[1:])

                            raw_multi_hop_routes.append(
                                {
                                    "leg1": {
                                        "trainNumber": leg1["trainNumber"],
                                        "trainName": leg1["trainName"],
                                        "type": leg1["type"],
                                        "departureTime": leg1["departureTime"],
                                        "arrivalTime": leg1["arrivalTime"],
                                        "durationMinutes": leg1["durationMinutes"],
                                        "subRoute": leg1["subRoute"],
                                    },
                                    "leg2": {
                                        "trainNumber": train_b.get("trainNumber"),
                                        "trainName": train_b.get("trainName"),
                                        "type": train_b.get("type"),
                                        "departureTime": dep_x_b,
                                        "arrivalTime": arr_b,
                                        "durationMinutes": dur_b,
                                        "subRoute": sub_route_b,
                                    },
                                    "transferStation": {
                                        "code": x_code,
                                        "name": leg1["transferStationName"]
                                        or stop_x.get("stationName"),
                                    },
                                    "layoverMinutes": layover,
                                    "totalJourneyMinutes": total_journey_mins,
                                    "combinedRoute": combined_route,
                                }
                            )

    # Step 3: Deduplicate identical combined station paths (keep fastest option)
    deduped_routes: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    for route_option in raw_multi_hop_routes:
        path_key = tuple(
            str(s.get("stationCode")).upper() for s in route_option["combinedRoute"]
        )
        if (
            path_key not in deduped_routes
            or route_option["totalJourneyMinutes"]
            < deduped_routes[path_key]["totalJourneyMinutes"]
        ):
            deduped_routes[path_key] = route_option

    sorted_routes = sorted(
        deduped_routes.values(), key=lambda r: r["totalJourneyMinutes"]
    )
    top_results = sorted_routes[:10]

    if return_stats:
        stats = {
            "candidates_before_backtrack": candidates_before_backtrack,
            "candidates_surviving_backtrack": len(raw_multi_hop_routes),
            "deduped_count": len(deduped_routes),
        }
        return top_results, stats

    return top_results


if __name__ == "__main__":
    print("=================================================================")
    print("      INDIAN RAILWAYS ROUTE SEARCH MODULE DEMO")
    print("=================================================================")

    client = MongoClient("mongodb://localhost:27017")
    db = client["train_recommendation_system"]

    # -------------------------------------------------------------------
    # TEST: Multi-Hop Backtracking Fix Verification (SSA -> BKN)
    # -------------------------------------------------------------------
    test_src, test_dst = "SSA", "BKN"  # Sirsa to Bikaner
    print(
        f"\n[FIX 1 TEST] Searching for routes: {test_src} (Sirsa) -> {test_dst} (Bikaner)..."
    )

    direct = find_direct_trains(test_src, test_dst, db)
    fastest_direct_dur = direct[0]["durationMinutes"] if direct else None

    print(f"[OK] Found {len(direct)} direct train(s).")

    multi, stats = find_multi_hop_trains(
        test_src, test_dst, db, compare_to_direct_duration=fastest_direct_dur, return_stats=True
    )

    print(f"[OK] Total multi-hop candidates evaluated before backtrack filter : {stats['candidates_before_backtrack']}")
    print(f"[OK] Total multi-hop candidates surviving strict backtrack filter : {stats['candidates_surviving_backtrack']}")
    print(f"[OK] New Total Result Count (Deduplicated & Capped)                : {len(multi)}")

    print(f"\nTop {min(3, len(multi))} Surviving Multi-Hop Transfer Options for {test_src} -> {test_dst}:")
    for idx, m in enumerate(multi[:3], 1):
        tot_hrs, tot_mins = divmod(m["totalJourneyMinutes"], 60)
        lay_hrs, lay_mins = divmod(m["layoverMinutes"], 60)

        print(f"\n--- Option #{idx}: Multi-Hop Journey ---")
        print(
            f"  Leg 1: Train #{m['leg1']['trainNumber']} ({m['leg1']['trainName']}) [{m['leg1']['type']}]"
        )
        print(
            f"         Departure: {m['leg1']['departureTime']} | Arrival at Transfer: {m['leg1']['arrivalTime']} (Duration: {m['leg1']['durationMinutes']} mins)"
        )
        print(
            f"  Transfer Station : {m['transferStation']['name']} ({m['transferStation']['code']}) [Layover: {lay_hrs}h {lay_mins}m / {m['layoverMinutes']} mins]"
        )
        print(
            f"  Leg 2: Train #{m['leg2']['trainNumber']} ({m['leg2']['trainName']}) [{m['leg2']['type']}]"
        )
        print(
            f"         Departure at Transfer: {m['leg2']['departureTime']} | Final Arrival: {m['leg2']['arrivalTime']} (Duration: {m['leg2']['durationMinutes']} mins)"
        )
        print(f"  Total Duration   : {tot_hrs}h {tot_mins}m ({m['totalJourneyMinutes']} mins)")
        print("  Combined Path    : " + " -> ".join([s["stationCode"] for s in m["combinedRoute"]]))
        print("-" * 65)

    print("\n=================================================================")
