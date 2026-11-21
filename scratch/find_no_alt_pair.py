import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import MongoClient
from recommend import get_recommendations


def routes_with_no_alt():
    db = MongoClient('mongodb://localhost:27017')['train_recommendation_system']
    sample_pairs = [
        ('JAT', 'UHP', '2026-11-15T06:30:00', '2026-11-15T05:00:00'),
        ('SBC', 'MYS', '2026-11-15T19:00:00', '2026-11-15T18:00:00'),
        ('NDLS', 'MAS', '2026-11-15T19:00:00', '2026-11-15T18:00:00'),
    ]

    for src, dst, scheduled_time, current_time in sample_pairs:
        result = get_recommendations(src, dst, scheduled_time, 180, 30, db, current_time=current_time)
        print(src, '->', dst, 'scheduled=', scheduled_time, 'current=', current_time, '=>', result['decision'], 'level=', result.get('level'), 'alts=', len(result.get('alternatives', [])))
        if src == 'NDLS' and dst == 'MAS' and result['decision'] == 'no_alternative_available':
            raise SystemExit('FAIL: NDLS -> MAS should return a practical alternative for a realistic future departure window')


if __name__ == '__main__':
    routes_with_no_alt()
