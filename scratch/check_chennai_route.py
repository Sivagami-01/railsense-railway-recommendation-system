import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import MongoClient


db = MongoClient('mongodb://localhost:27017')['train_recommendation_system']
for src, dst in [('MAS', 'MSB'), ('MAS', 'MS'), ('MSB', 'MAS')]:
    hits = []
    for t in db.trains.find({'completeOrderedRoute.stationCode': src}, {'trainNumber': 1, 'trainName': 1, 'type': 1, 'completeOrderedRoute': 1}):
        route = [s.get('stationCode') for s in t.get('completeOrderedRoute', []) if s.get('stationCode')]
        if dst in route:
            hits.append(t)
    print(src, '->', dst, 'count=', len(hits))
    for t in hits[:3]:
        route = t.get('completeOrderedRoute', [])
        src_idx = next((i for i, s in enumerate(route) if s.get('stationCode') == src), None)
        dst_idx = next((i for i, s in enumerate(route) if s.get('stationCode') == dst), None)
        if src_idx is not None and dst_idx is not None and src_idx < dst_idx:
            sub = route[src_idx:dst_idx + 1]
            print(' ', t.get('trainNumber'), t.get('trainName'), t.get('type'), sub[0].get('departureTime'), sub[-1].get('arrivalTime'))
