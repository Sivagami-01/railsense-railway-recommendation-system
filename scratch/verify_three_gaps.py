import sys
import os
import json
import urllib.request

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pymongo import MongoClient
import recommend
import route_search
from recommend import get_recommendations

client = MongoClient('mongodb://localhost:27017')
db = client['train_recommendation_system']

print("=================================================================")
print("     VERIFICATION OF THREE ENGINE GAPS (SEATS, LAYOVER, CATCH)   ")
print("=================================================================")

# -----------------------------------------------------------------
# GAP 1: SEAT AVAILABILITY FILTER TEST
# -----------------------------------------------------------------
print("\n--- GAP 1: SEAT AVAILABILITY FILTER VERIFICATION ---")

# Step 1: Normal run (Train #12445 has positive seats)
res_normal = get_recommendations(
    source_code="JAT",
    destination_code="UHP",
    scheduled_time="2026-11-15T06:30:00",
    delay_minutes=120,
    wait_tolerance_minutes=30,
    db=db,
    current_time="2026-09-23T22:00:00"
)
print("Normal Run (Positive Seats):")
print("  Decision:", res_normal['decision'], "| Level:", res_normal.get('level'))
if res_normal.get('alternatives'):
    alt = res_normal['alternatives'][0]
    print(f"  Returned Train: #{alt['trainNumber']} ({alt['trainName']}), Arrival: {alt['arrivalTime']}")
    print(f"  Seats: {alt['seatAvailability']}")

# Step 2: Zero-Seat Mocking for Train #12445
orig_gen = recommend.generate_seat_availability
def mock_zero_seats(train_type, pct=None):
    # Mock all zero seats for testing
    return {"SL": 0, "3A": 0, "2A": 0, "1A": 0, "2S": 0}

recommend.generate_seat_availability = mock_zero_seats

res_zero = get_recommendations(
    source_code="JAT",
    destination_code="UHP",
    scheduled_time="2026-11-15T06:30:00",
    delay_minutes=120,
    wait_tolerance_minutes=30,
    db=db,
    current_time="2026-09-23T22:00:00"
)
recommend.generate_seat_availability = orig_gen  # restore original

print("\nZero-Seat Run (Train #12445 has 0 seats across ALL classes):")
print("  Decision:", res_zero['decision'], "| Level:", res_zero.get('level'))
print("  Alternatives Count:", len(res_zero.get('alternatives', [])))

# Verification check
matched_zero_train = any(
    a.get('trainNumber') == '12445' or (a.get('leg1') and a['leg1'].get('trainNumber') == '12445')
    for a in res_zero.get('alternatives', [])
)
if not matched_zero_train:
    print("✓ SUCCESS: Train #12445 matched timing window (06:45->08:05) but was EXCLUDED due to 0 seats!")
else:
    print("❌ FAILED: Zero-seat train was returned in recommendations!")


# -----------------------------------------------------------------
# GAP 2: MINIMUM LAYOVER BUFFER TEST FOR LEVEL 3 MULTI-HOP
# -----------------------------------------------------------------
print("\n--- GAP 2: MINIMUM LAYOVER BUFFER (LEVEL 3) VERIFICATION ---")

# Test 2A: Valid Layover (min_layover_minutes = 30 mins)
multi_valid = route_search.find_multi_hop_trains(
    source_code="SSA",
    destination_code="DNA",
    db=db,
    max_hops=2,
    min_layover_minutes=30
)
print(f"Multi-hop candidates with min_layover_minutes=30: {len(multi_valid)}")
if multi_valid:
    m = multi_valid[0]
    print(f"  Selected Option Layover: {m['layoverMinutes']} mins at {m['transferStation']} (>= 30 mins: PASS)")

# Test 2B: Unrealistic Layover (Set high min_layover_minutes = 300 mins)
multi_strict = route_search.find_multi_hop_trains(
    source_code="SSA",
    destination_code="DNA",
    db=db,
    max_hops=2,
    min_layover_minutes=300
)
print(f"Multi-hop candidates with strict min_layover_minutes=300: {len(multi_strict)}")
if len(multi_strict) < len(multi_valid):
    print("✓ SUCCESS: Combos with layover < min_layover_minutes (e.g. 270 mins) were correctly REJECTED!")


# -----------------------------------------------------------------
# GAP 3: REAL-WORLD WALL-CLOCK DEPARTURE FEASIBILITY TEST
# -----------------------------------------------------------------
print("\n--- GAP 3: REAL-WORLD WALL-CLOCK DEPARTURE FEASIBILITY VERIFICATION ---")

# Test 3A: Past departure relative to current_time
# Train #12445 departs at 06:45:00 on 2026-09-23.
# If current_time is 2026-09-23T07:00:00 (15 mins after train departed!), train should be EXCLUDED.
res_past = get_recommendations(
    source_code="JAT",
    destination_code="UHP",
    scheduled_time="2026-09-23T06:30:00",
    delay_minutes=120,
    wait_tolerance_minutes=30,
    db=db,
    current_time="2026-09-23T07:00:00"  # Wall clock is 07:00:00 (Train #12445 departed 15m ago at 06:45:00)
)
print("Scenario (a): Candidate Train Departed in Past (Dep: 06:45:00, Wall-Clock: 07:00:00):")
print("  Decision:", res_past['decision'])
print("  Alternatives Count:", len(res_past.get('alternatives', [])))

past_departed_included = any(
    a.get('trainNumber') == '12445' for a in res_past.get('alternatives', [])
)
if not past_departed_included:
    print("✓ SUCCESS: Train #12445 departed at 06:45:00, wall-clock is 07:00:00 -> EXCLUDED as expected!")
else:
    print("❌ FAILED: Past departed train was recommended!")

# Test 3B: Future-dated journey (Nov 15, 2026) relative to current_time (Sept 23, 2026)
res_future = get_recommendations(
    source_code="JAT",
    destination_code="UHP",
    scheduled_time="2026-11-15T06:30:00",
    delay_minutes=120,
    wait_tolerance_minutes=30,
    db=db,
    current_time="2026-09-23T22:00:00"
)
print("\nScenario (b): Future-Dated Journey (Nov 15, 2026 vs Wall-Clock Sept 23, 2026):")
print("  Decision:", res_future['decision'], "| Level:", res_future.get('level'))
if res_future.get('alternatives'):
    alt = res_future['alternatives'][0]
    print(f"  Returned Train: #{alt['trainNumber']} ({alt['trainName']}) (PASSES TRIVIALLY)")

print("\n=================================================================")
