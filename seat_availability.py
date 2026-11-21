"""
Seat Availability Mock Data Generator Module
----------------------------------------------
Generates realistic mock seat availability data for Indian Railways train types
based on train classification and historical seat utilization percentages.
"""

import random
from typing import Dict, List, Optional

# Dict mapping train_type to available classes and realistic total train capacity per class
TRAIN_CLASS_CAPACITIES: Dict[str, Dict[str, int]] = {
    "Superfast Express": {
        "SL": 504,  # ~7 coaches x 72 berths
        "3A": 256,  # ~4 coaches x 64 berths
        "2A": 92,   # ~2 coaches x 46 berths
        "1A": 18,   # ~1 coach x 18 berths
        "2S": 216,  # ~2 coaches x 108 seats
    },
    "Vande Bharat Express": {
        "CC": 546,  # ~7 coaches x 78 seats
        "EC": 104,  # ~2 coaches x 52 seats
    },
    "DEMU/MEMU": {
        "2S": 648,  # ~6 coaches x 108 seats
    },
    "Passenger Train": {
        "2S": 540,  # ~5 coaches x 108 seats
        "SL": 144,  # ~2 coaches x 72 berths
    },
    "Rajdhani Express": {
        "1A": 36,   # ~2 coaches x 18 berths
        "2A": 184,  # ~4 coaches x 46 berths
        "3A": 384,  # ~6 coaches x 64 berths
    },
    "Garib Rath Express": {
        "3A": 576,  # ~9 coaches x 64 berths
        "CC": 156,  # ~2 coaches x 78 seats
    },
    "Duronto Express": {
        "1A": 18,   # ~1 coach x 18 berths
        "2A": 138,  # ~3 coaches x 46 berths
        "3A": 384,  # ~6 coaches x 64 berths
        "SL": 288,  # ~4 coaches x 72 berths
    },
    "Humsafar Express": {
        "3A": 640,  # ~10 coaches x 64 berths
    },
    "Intercity Express": {
        "CC": 312,  # ~4 coaches x 78 seats
        "2S": 432,  # ~4 coaches x 108 seats
        "3A": 128,  # ~2 coaches x 64 berths
    },
    "Jan Shatabdi Express": {
        "CC": 234,  # ~3 coaches x 78 seats
        "2S": 540,  # ~5 coaches x 108 seats
    },
    "Mail/Express": {
        "SL": 432,  # ~6 coaches x 72 berths
        "3A": 192,  # ~3 coaches x 64 berths
        "2A": 92,   # ~2 coaches x 46 berths
        "1A": 18,   # ~1 coach x 18 berths
        "2S": 216,  # ~2 coaches x 108 seats
    },
}

TYPE_ALIAS_MAP: Dict[str, str] = {
    "SF": "Superfast Express",
    "SUPERFAST": "Superfast Express",
    "DEMU": "DEMU/MEMU",
    "MEMU": "DEMU/MEMU",
    "PASS": "Passenger Train",
    "PASSENGER": "Passenger Train",
    "RAJ": "Rajdhani Express",
    "RAJDHANI": "Rajdhani Express",
    "GR": "Garib Rath Express",
    "GARIB RATH": "Garib Rath Express",
    "DRNT": "Duronto Express",
    "DURONTO": "Duronto Express",
    "HUMSAFAR": "Humsafar Express",
    "INTERCITY": "Intercity Express",
    "JSHTB": "Jan Shatabdi Express",
    "JAN SHATABDI": "Jan Shatabdi Express",
    "SHTB": "Intercity Express",
    "SHATABDI": "Intercity Express",
    "EXP": "Mail/Express",
    "EXPRESS": "Mail/Express",
    "MAIL": "Mail/Express",
    "SKR": "Mail/Express",
    "DEL": "Mail/Express",
    "HYD": "Mail/Express",
    "KLKT": "Mail/Express",
    "TOY": "Passenger Train",
}


def generate_seat_availability(
    train_type: str, seat_utilisation_pct: Optional[float] = None
) -> Dict[str, int]:
    """
    Generates mock available seat counts per class for a given train_type.

    Args:
        train_type: Type of train (e.g. "Vande Bharat Express", "Rajdhani Express", "SF", "DEMU").
        seat_utilisation_pct: Historical seat utilization percentage (0 to 100).
                               If None or omitted, defaults to a random value between 40% and 95%.

    Returns:
        Dict[str, int]: Dictionary mapping class codes (e.g. {"SL": 45, "3A": 12})
                        to remaining available seats. Minimum value is 0.
    """
    # Lookup capacities for train_type using alias map and case-insensitive fallback
    alias_type = TYPE_ALIAS_MAP.get(str(train_type).strip().upper())
    target_type = alias_type or train_type

    capacities = TRAIN_CLASS_CAPACITIES.get(target_type)
    if capacities is None:
        normalized_type = str(target_type).strip().lower()
        for known_type, caps in TRAIN_CLASS_CAPACITIES.items():
            if known_type.lower() == normalized_type:
                capacities = caps
                break

    if capacities is None:
        capacities = TRAIN_CLASS_CAPACITIES[DEFAULT_TRAIN_TYPE]

    # Handle missing utilization percentage
    if seat_utilisation_pct is None:
        utilisation = random.uniform(40.0, 95.0)
    else:
        utilisation = max(0.0, min(100.0, float(seat_utilisation_pct)))

    availability: Dict[str, int] = {}

    for seat_class, total_capacity in capacities.items():
        # Compute available seats: total_capacity * (1 - utilisation_pct / 100)
        base_available = total_capacity * (1.0 - utilisation / 100.0)

        # Add random noise (±10%, i.e., multiplier between 0.90 and 1.10)
        noise = random.uniform(0.90, 1.10)
        noisy_available = base_available * noise

        # Round to nearest integer and ensure minimum of 0
        available_seats = max(0, int(round(noisy_available)))
        availability[seat_class] = available_seats

    return availability


def refresh_availability(current_availability: Dict[str, int]) -> Dict[str, int]:
    """
    Simulates live seat updates by re-randomizing seat counts slightly.
    Keeps new seat numbers within ±15% of the last value.

    Args:
        current_availability: Dict mapping class codes to current available seats.

    Returns:
        Dict[str, int]: Updated dict with refreshed seat counts (min 0).
    """
    refreshed: Dict[str, int] = {}
    for seat_class, count in current_availability.items():
        # Multiply current count by a random factor between 0.85 and 1.15 (±15%)
        factor = random.uniform(0.85, 1.15)
        new_count = int(round(count * factor))
        
        # If 0 seats, small chance of cancellation opening 1-2 seats
        if count == 0 and random.random() < 0.10:
            new_count = random.randint(1, 2)

        refreshed[seat_class] = max(0, new_count)

    return refreshed


if __name__ == "__main__":
    print("==========================================================")
    print("   MOCK SEAT AVAILABILITY GENERATOR - EXAMPLE DEMOS")
    print("==========================================================")

    # Example 1: Premium High-Speed Train with high utilization
    t1_type = "Vande Bharat Express"
    t1_util = 85.0
    avail1 = generate_seat_availability(t1_type, seat_utilisation_pct=t1_util)
    print(f"\nExample 1: {t1_type} (Historical Utilisation: {t1_util}%)")
    print(f"Initial Availability : {avail1}")
    avail1_refreshed = refresh_availability(avail1)
    print(f"Refreshed (Live Update): {avail1_refreshed}")

    # Example 2: Premium Express with default (random) utilization
    t2_type = "Rajdhani Express"
    avail2 = generate_seat_availability(t2_type)
    print(f"\nExample 2: {t2_type} (Default Random Utilisation)")
    print(f"Initial Availability : {avail2}")
    avail2_refreshed = refresh_availability(avail2)
    print(f"Refreshed (Live Update): {avail2_refreshed}")

    # Example 3: Commuter / Regional train with explicit utilization
    t3_type = "DEMU/MEMU"
    t3_util = 60.0
    avail3 = generate_seat_availability(t3_type, seat_utilisation_pct=t3_util)
    print(f"\nExample 3: {t3_type} (Historical Utilisation: {t3_util}%)")
    print(f"Initial Availability : {avail3}")
    avail3_refreshed = refresh_availability(avail3)
    print(f"Refreshed (Live Update): {avail3_refreshed}")

    print("\n==========================================================")
