import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from api import app


class TestAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @patch("api.get_recent_blocking_rates")
    def test_blocking_rates_endpoint(self, mock_get_rates):
        mock_get_rates.return_value = [
            {
                "collected_at_utc": "2026-11-21T21:50:00+00:00",
                "total_queries": 1000,
                "blocked_queries": 150,
                "block_percentage": 15.0,
            }
        ]

        response = self.client.get(
            "/api/dns/blocking-rates?limit=1"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            mock_get_rates.return_value,
        )
        mock_get_rates.assert_called_once_with(1)
    @patch("api.get_recent_blocking_rates")
    def test_blocking_rates_rejects_invalid_limits(self, mock_get_rates):
        invalid_limits = [0, 101, "abc"]

        for limit in invalid_limits:
            with self.subTest(limit=limit):
                response = self.client.get(
                    "/api/dns/blocking-rates",
                    params={"limit": limit},
                )

                self.assertEqual(response.status_code, 422)

        mock_get_rates.assert_not_called()
