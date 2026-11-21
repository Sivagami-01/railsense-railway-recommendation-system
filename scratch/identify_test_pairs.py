import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pymongo import MongoClient
import json
from route_search import find_direct_trains, find_multi_hop_trains
from recommend import get_recommendations

client = MongoClient('mongodb://localhost:27017')
db = client['train_recommendation_system']

print("=== IDENTIFYING TEST PAIRS & VALIDATING BACKEND ENGINE ===")

# Pair 1: Direct Express Winner
res1 = get_recommendations('JAT', 'UHP', '2026-11-15T06:30:00', 120, 30, db)
print("\n1. Level 1 Express (JAT -> UHP):")
print("Decision:", res1['decision'], "| Level:", res1.get('level'))
if res1.get('alternatives'):
    alt = res1['alternatives'][0]
    print(f"  Train: {alt['trainNumber']} {alt['trainName']} ({alt['type']})")
    print(f"  Departure: {alt['departureTime']} | Arrival: {alt['arrivalTime']} | Duration: {alt['durationMinutes']}m")
    print(f"  Station Sequence: {alt['stationSequence']}")
    print(f"  Seat Availability: {alt['seatAvailability']}")

# Pair 2: Direct Local/Passenger Winner
res2 = get_recommendations('JAT', 'UHP', '2026-11-15T17:25:00', 30, 15, db)
print("\n2. Level 2 Passenger (JAT -> UHP):")
print("Decision:", res2['decision'], "| Level:", res2.get('level'))
if res2.get('alternatives'):
    alt = res2['alternatives'][0]
    print(f"  Train: {alt['trainNumber']} {alt['trainName']} ({alt['type']})")
    print(f"  Departure: {alt['departureTime']} | Arrival: {alt['arrivalTime']} | Duration: {alt['durationMinutes']}m")
    print(f"  Station Sequence: {alt['stationSequence']}")

# Pair 3: Level 3 Multi-hop Winner
res3 = get_recommendations('SSA', 'DNA', '2026-11-16T09:30:00', 180, 30, db)
print("\n3. Level 3 Multi-hop (SSA -> DNA):")
print("Decision:", res3['decision'], "| Level:", res3.get('level'))
if res3.get('alternatives'):
    alt = res3['alternatives'][0]
    print("  Leg 1:", alt['leg1']['trainNumber'], alt['leg1']['trainName'], alt['leg1']['departureTime'], "->", alt['leg1']['arrivalTime'])
    print("  Leg 1 Sequence:", alt['leg1']['stationSequence'])
    print("  Leg 1 Seats:", alt['leg1']['seatAvailability'])
    print("  Transfer Station:", alt['transferStation'])
    print("  Layover Minutes:", alt['layoverMinutes'])
    print("  Leg 2:", alt['leg2']['trainNumber'], alt['leg2']['trainName'], alt['leg2']['departureTime'], "->", alt['leg2']['arrivalTime'])
    print("  Leg 2 Sequence:", alt['leg2']['stationSequence'])
    print("  Leg 2 Seats:", alt['leg2']['seatAvailability'])
    print("  Total Duration:", alt['totalDurationMinutes'])

# Pair 4: Overnight Past Midnight (SSA -> HSR)
res5 = get_recommendations('SSA', 'HSR', '2026-11-16T00:10:00', 60, 10, db)
print("\n4. Overnight Past-Midnight (SSA -> HSR):")
print("Decision:", res5['decision'], "| Level:", res5.get('level'))
if res5.get('alternatives'):
    alt = res5['alternatives'][0]
    print(f"  Train: {alt['trainNumber']} {alt['trainName']} ({alt['type']})")
    print(f"  Departure: {alt['departureTime']} | Arrival: {alt['arrivalTime']}")
