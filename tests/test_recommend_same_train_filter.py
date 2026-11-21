import unittest
from unittest.mock import MagicMock, patch

from recommend import get_recommendations


class FakeStationsCollection:
    def find_one(self, query):
        if query.get("code") in {"JAT", "UHP"}:
            return {"code": query["code"]}
        return None

    def find(self, *args, **kwargs):
        return []


class RecommendationFilterTests(unittest.TestCase):
    @patch("recommend.generate_seat_availability", return_value={"CC": 10, "SL": 5})
    @patch("recommend.find_direct_trains")
    def test_excludes_booked_train_from_alternatives(self, mock_find_direct_trains, _mock_seats):
        db = MagicMock()
        db.stations = FakeStationsCollection()
        scheduled_time = "2026-11-15T06:30:00"

        mock_find_direct_trains.return_value = [
            {
                "trainNumber": "123",
                "trainName": "Booked Train",
                "type": "Superfast",
                "departureTimeAtSource": "06:00:00",
                "arrivalTimeAtDestination": "08:15:00",
                "durationMinutes": 135,
                "subRoute": [
                    {"stationCode": "JAT"},
                    {"stationCode": "UHP"},
                ],
            },
            {
                "trainNumber": "456",
                "trainName": "Alternate Train",
                "type": "Express",
                "departureTimeAtSource": "07:05:00",
                "arrivalTimeAtDestination": "08:20:00",
                "durationMinutes": 75,
                "subRoute": [
                    {"stationCode": "JAT"},
                    {"stationCode": "UHP"},
                ],
            },
        ]

        result = get_recommendations(
            source_code="JAT",
            destination_code="UHP",
            scheduled_time=scheduled_time,
            delay_minutes=120,
            wait_tolerance_minutes=30,
            db=db,
            booked_train_number="123",
            current_time="2026-11-15T05:00:00",
        )

        self.assertEqual(result["decision"], "alternative_found")
        self.assertEqual([alt["trainNumber"] for alt in result["alternatives"]], ["456"])


if __name__ == "__main__":
    unittest.main()
