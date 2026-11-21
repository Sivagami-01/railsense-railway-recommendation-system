import sys
from pathlib import Path
from random import sample

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import MongoClient
from recommend import get_recommendations


def find_issues(limit=20):
    db = MongoClient('mongodb://localhost:27017')['train_recommendation_system']
    station_codes = [s['code'] for s in db.stations.find({}, {'code': 1})]
    pair_set = set()
    for src in station_codes:
        if len(pair_set) >= limit * 4:
            break
        for dst in sample(station_codes, min(20, len(station_codes))):
            if src == dst:
                continue
            # keep a small set of combinations with real routes
            hits = list(db.trains.find({'completeOrderedRoute.stationCode': src}, {'trainNumber': 1, 'completeOrderedRoute': 1}).limit(10))
            for t in hits:
                route = [s.get('stationCode') for s in t.get('completeOrderedRoute', []) if s.get('stationCode')]
                if dst in route and (src, dst) not in pair_set:
                    pair_set.add((src, dst))
                    break
    print('pairs', len(pair_set))
    for src, dst in list(pair_set)[:limit]:
        # nearest future schedule window on same day to avoid impossible constraints
        scheduled_time = f'2026-11-15T15:00:00'
        current_time = '2026-11-15T12:00:00'
        result = get_recommendations(src, dst, scheduled_time, 150, 30, db, current_time=current_time)
        if result['decision'] == 'no_alternative_available':
            print('NO_ALT', src, dst, result)


if __name__ == '__main__':
    find_issues()
