import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import MongoClient
from recommend import get_recommendations


def check(label, src, dst, scheduled_time, delay_minutes, wait_tolerance, current_time):
    db = MongoClient('mongodb://localhost:27017')['train_recommendation_system']
    result = get_recommendations(
        src,
        dst,
        scheduled_time,
        delay_minutes,
        wait_tolerance,
        db,
        current_time=current_time,
    )
    print(label, '=>', result['decision'], 'level=', result.get('level'), 'alts=', len(result.get('alternatives', [])))
    return result


if __name__ == '__main__':
    # These should return practical alternatives under a realistic "future / valid journey" check.
    scenarios = [
        ('JAT_UHP_future', 'JAT', 'UHP', '2026-11-15T06:30:00', 120, 30, '2026-11-15T05:00:00'),
        ('SBC_MYS_evening', 'SBC', 'MYS', '2026-11-15T19:00:00', 180, 30, '2026-11-15T18:00:00'),
    ]

    for label, src, dst, scheduled_time, delay, tolerance, current_time in scenarios:
        result = check(label, src, dst, scheduled_time, delay, tolerance, current_time)
        if result['decision'] == 'no_alternative_available':
            raise SystemExit(f'FAIL: {label} returned no_alternative_available')
