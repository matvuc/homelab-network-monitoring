
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import closing
from analytics import get_recent_blocking_rates
from analytics import get_recent_blocking_rates, get_snapshot_history

class TestAnalytics(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute("""
                CREATE TABLE dns_snapshots (
                    id INTEGER PRIMARY KEY,
                    collected_at_utc TEXT NOT NULL,
                    total_queries INTEGER NOT NULL,
                    blocked_queries INTEGER NOT NULL
                )
            """)

            conn.executemany(
                """
                INSERT INTO dns_snapshots
                (collected_at_utc, total_queries, blocked_queries)
                VALUES (?, ?, ?)
                """,
                [
                    ("2026-11-21T10:00:00+00:00", 100, 20),
                    ("2026-11-21T10:05:00+00:00", 200, 50),
                    ("2026-11-21T10:10:00+00:00", 400, 80),
                ],
            )

        self.patcher = patch("analytics.DB_PATH", self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_returns_requested_number_of_snapshots(self):
        results = get_recent_blocking_rates(2)
        self.assertEqual(len(results), 2)

    def test_returns_newest_snapshot_first(self):
        results = get_recent_blocking_rates(3)
        self.assertEqual(results[0]["total_queries"], 400)

    def test_calculates_blocking_percentage(self):
        results = get_recent_blocking_rates(3)
        self.assertEqual(results[0]["block_percentage"], 20.0)

    def test_rejects_invalid_limit(self):
        with self.assertRaises(ValueError):
            get_recent_blocking_rates(0)
    
    def test_handles_zero_total_queries(self):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                """
                INSERT INTO dns_snapshots
                (collected_at_utc, total_queries, blocked_queries)
                VALUES (?, ?, ?)
                """,
                ("2026-11-21T10:15:00+00:00", 0, 0),
            )

        results = get_recent_blocking_rates(1)

        self.assertIsNone(results[0]["block_percentage"])

    def test_returns_empty_list_when_no_snapshots(self):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute("DELETE FROM dns_snapshots")

        results = get_recent_blocking_rates(10)

        self.assertEqual(results, [])

    
    def test_history_filters_time_range(self):
        results = get_snapshot_history(
            "2026-11-21T10:05:00+00:00",
            "2026-11-21T10:10:00+00:00",
        )

        self.assertEqual(len(results), 2)

    def test_history_returns_chronological_order(self):
        results = get_snapshot_history(
            "2026-11-21T10:00:00+00:00",
            "2026-11-21T10:10:00+00:00",
        )

        self.assertEqual(
            [row["total_queries"] for row in results],
            [100, 200, 400],
        )

    def test_history_rejects_reversed_time_range(self):
        with self.assertRaises(ValueError):
            get_snapshot_history(
                "2026-11-21T10:10:00+00:00",
                "2026-11-21T10:00:00+00:00",
            )

    
    def test_history_rejects_invalid_timestamp(self):
        with self.assertRaises(ValueError):
            get_snapshot_history(
                "not-a-date",
                "2026-11-21T10:10:00+00:00",
            )

    def test_history_rejects_missing_timezone(self):
        with self.assertRaises(ValueError):
            get_snapshot_history(
                "2026-11-21T10:00:00",
                "2026-11-21T10:10:00+00:00",
            )

    def test_history_converts_timezone_to_utc(self):
        results = get_snapshot_history(
            "2026-11-21T04:05:00-06:00",
            "2026-11-21T04:10:00-06:00",
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["total_queries"], 200)
        self.assertEqual(results[1]["total_queries"], 400)

