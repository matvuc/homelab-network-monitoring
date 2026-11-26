import sqlite3
import tempfile
import unittest

from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from analytics import get_hourly_aggregates
from database import SCHEMA_PATH


class TestHeatmap(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.executescript(SCHEMA_PATH.read_text())

        self.patcher = patch("analytics.DB_PATH", self.db_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def insert_rows(self, rows):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.executemany(
                """
                INSERT INTO dns_snapshots
                (collected_at_utc, total_queries, blocked_queries)
                VALUES (?, ?, ?)
                """,
                rows,
            )

    def test_hourly_aggregation_arithmetic(self):
        self.insert_rows([
            ("2026-11-21T10:00:00+00:00", 100, 10),
            ("2026-11-21T10:05:00+00:00", 200, 40),
            ("2026-11-21T10:10:00+00:00", 0, 0),
        ])

        results = get_hourly_aggregates(
            "2026-11-21T10:00:00+00:00",
            "2026-11-21T11:00:00+00:00",
        )

        self.assertEqual(len(results), 1)
        row = results[0]

        self.assertEqual(row["snapshot_count"], 3)
        self.assertEqual(row["valid_blocking_samples"], 2)
        self.assertAlmostEqual(row["avg_block_percentage"], 15.0)
        self.assertAlmostEqual(row["avg_rolling_queries"], 100.0)

    def test_hourly_range_boundaries(self):
        self.insert_rows([
            ("2026-11-21T09:59:59.999999+00:00", 100, 10),
            ("2026-11-21T10:00:00+00:00", 200, 20),
            ("2026-11-21T10:59:59.999999+00:00", 300, 30),
            ("2026-11-21T11:00:00+00:00", 400, 40),
        ])

        results = get_hourly_aggregates(
            "2026-11-21T10:00:00+00:00",
            "2026-11-21T11:00:00+00:00",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["snapshot_count"], 2)
        self.assertAlmostEqual(
            results[0]["avg_rolling_queries"], 250.0
        )

    def test_all_zero_query_totals(self):
        self.insert_rows([
            ("2026-11-21T10:00:00+00:00", 0, 0),
            ("2026-11-21T10:05:00+00:00", 0, 0),
        ])

        results = get_hourly_aggregates(
            "2026-11-21T10:00:00+00:00",
            "2026-11-21T11:00:00+00:00",
        )

        row = results[0]

        self.assertEqual(row["snapshot_count"], 2)
        self.assertEqual(row["valid_blocking_samples"], 0)
        self.assertIsNone(row["avg_block_percentage"])
        self.assertEqual(row["avg_rolling_queries"], 0.0)

    def test_valid_zero_blocking_rate(self):
        self.insert_rows([
            ("2026-11-21T10:00:00+00:00", 100, 0),
        ])

        results = get_hourly_aggregates(
            "2026-11-21T10:00:00+00:00",
            "2026-11-21T11:00:00+00:00",
        )

        self.assertEqual(results[0]["avg_block_percentage"], 0.0)
        self.assertEqual(results[0]["valid_blocking_samples"], 1)

    def test_empty_database(self):
        results = get_hourly_aggregates(
            "2026-11-21T10:00:00+00:00",
            "2026-11-21T11:00:00+00:00",
        )

        self.assertEqual(results, [])

    def test_aggregation_exceeds_history_limit(self):
        start = datetime(2026, 11, 21, tzinfo=timezone.utc)

        self.insert_rows([
            (
                (start + timedelta(minutes=5 * i)).isoformat(),
                1000,
                200,
            )
            for i in range(1500)
        ])

        results = get_hourly_aggregates(
            start.isoformat(),
            (start + timedelta(days=7)).isoformat(),
        )

        self.assertEqual(
            sum(row["snapshot_count"] for row in results),
            1500,
        )
        self.assertEqual(len(results), 125)

    def test_normal_calendar_week(self):
        from analytics import _build_heatmap_calendar

        now = datetime.fromisoformat(
            "2026-11-26T00:30:00+00:00"
        )

        dates, start, end, hours = _build_heatmap_calendar(now)

        self.assertEqual(len(dates), 7)
        self.assertEqual(len(hours), 168)
        self.assertEqual(dates[0], "2026-11-19")
        self.assertEqual(dates[-1], "2026-11-25")

        self.assertEqual(
            start.isoformat(), "2026-11-19T06:00:00+00:00"
        )
        self.assertEqual(
            end.isoformat(), "2026-11-26T06:00:00+00:00"
        )

        current = [
            hour for hour in hours
            if hour["status"] == "current"
        ]

        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["local_hour"], 18)
        self.assertEqual(current[0]["local_date"], "2026-11-25")

    def test_spring_forward_calendar(self):
        from analytics import _build_heatmap_calendar

        now = datetime.fromisoformat(
            "2026-03-08T18:00:00+00:00"
        )

        dates, start, end, hours = _build_heatmap_calendar(now)

        self.assertEqual(len(dates), 7)
        self.assertEqual(len(hours), 167)

        transition_hours = [
            hour["local_hour"]
            for hour in hours
            if hour["local_date"] == "2026-03-08"
        ]

        self.assertEqual(len(transition_hours), 23)
        self.assertNotIn(2, transition_hours)

    def test_fall_back_calendar(self):
        from analytics import _build_heatmap_calendar

        now = datetime.fromisoformat(
            "2026-11-01T18:00:00+00:00"
        )

        dates, start, end, hours = _build_heatmap_calendar(now)

        self.assertEqual(len(dates), 7)
        self.assertEqual(len(hours), 169)

        repeated = [
            hour for hour in hours
            if hour["local_date"] == "2026-11-01"
            and hour["local_hour"] == 1
        ]

        self.assertEqual(len(repeated), 2)

        self.assertEqual(
            [hour["utc_offset"] for hour in repeated],
            ["-05:00", "-06:00"],
        )

        self.assertNotEqual(
            repeated[0]["hour_start_utc"],
            repeated[1]["hour_start_utc"],
        )

    def test_heatmap_hour_statuses(self):
        from analytics import get_dns_heatmap

        now = datetime.fromisoformat(
            "2026-11-26T00:30:00+00:00"
        )

        self.insert_rows([
            ("2026-11-25T23:05:00+00:00", 100, 20),
            ("2026-11-26T00:05:00+00:00", 200, 40),
            ("2026-11-26T00:30:00+00:00", 500, 100),
            ("2026-11-26T00:35:00+00:00", 900, 300),
            ("2026-11-26T01:05:00+00:00", 400, 80),
        ])

        result = get_dns_heatmap(now)

        self.assertEqual(result["timezone"], "America/Chicago")
        self.assertEqual(len(result["dates"]), 7)
        self.assertEqual(len(result["hours"]), 168)

        hours = {
            hour["hour_start_utc"]: hour
            for hour in result["hours"]
        }

        observed = hours["2026-11-25T23:00:00+00:00"]
        missing = hours["2026-11-25T22:00:00+00:00"]
        current = hours["2026-11-26T00:00:00+00:00"]
        future = hours["2026-11-26T01:00:00+00:00"]

        self.assertEqual(observed["status"], "observed")
        self.assertEqual(observed["snapshot_count"], 1)
        self.assertAlmostEqual(
            observed["avg_block_percentage"], 20.0
        )

        self.assertEqual(missing["status"], "missing")
        self.assertEqual(missing["snapshot_count"], 0)
        self.assertIsNone(missing["avg_block_percentage"])
        self.assertIsNone(missing["avg_rolling_queries"])

        self.assertEqual(current["status"], "current")
        self.assertEqual(current["snapshot_count"], 1)
        self.assertEqual(current["avg_rolling_queries"], 200.0)

        self.assertEqual(future["status"], "future")
        self.assertIsNone(future["snapshot_count"])
        self.assertIsNone(future["avg_block_percentage"])
        self.assertIsNone(future["avg_rolling_queries"])

    def test_heatmap_empty_database(self):
        from analytics import get_dns_heatmap
        from collections import Counter

        now = datetime.fromisoformat(
            "2026-11-26T00:30:00+00:00"
        )

        result = get_dns_heatmap(now)

        statuses = Counter(
            hour["status"] for hour in result["hours"]
        )

        self.assertEqual(len(result["dates"]), 7)
        self.assertEqual(len(result["hours"]), 168)
        self.assertEqual(statuses["observed"], 0)
        self.assertEqual(statuses["missing"], 162)
        self.assertEqual(statuses["current"], 1)
        self.assertEqual(statuses["future"], 5)

    def test_heatmap_rejects_naive_datetime(self):
        from analytics import get_dns_heatmap

        with self.assertRaises(ValueError):
            get_dns_heatmap(datetime(2026, 11, 25, 12, 0))

    def test_aggregation_rejects_invalid_ranges(self):
        valid = "2026-11-21T10:00:00+00:00"

        cases = [
            ("not-a-date", valid),
            ("2026-11-21T09:00:00", valid),
            (valid, valid),
            ("2026-11-21T11:00:00+00:00", valid),
        ]

        for start, end in cases:
            with self.subTest(start=start, end=end):
                with self.assertRaises(ValueError):
                    get_hourly_aggregates(start, end)

    def test_aggregation_normalizes_timezone(self):
        self.insert_rows([
            ("2026-11-21T10:05:00+00:00", 100, 20),
        ])

        results = get_hourly_aggregates(
            "2026-11-21T04:00:00-06:00",
            "2026-11-21T05:00:00-06:00",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["hour_start_utc"],
            "2026-11-21T10:00:00+00:00",
        )

    def test_repeated_dst_hours_keep_separate_metrics(self):
        from analytics import get_dns_heatmap

        self.insert_rows([
            ("2026-11-01T06:05:00+00:00", 100, 10),
            ("2026-11-01T07:05:00+00:00", 200, 60),
        ])

        now = datetime.fromisoformat(
            "2026-11-01T18:00:00+00:00"
        )

        result = get_dns_heatmap(now)

        repeated = [
            hour for hour in result["hours"]
            if hour["local_date"] == "2026-11-01"
            and hour["local_hour"] == 1
        ]

        self.assertEqual(len(repeated), 2)
        self.assertEqual(
            [hour["avg_block_percentage"] for hour in repeated],
            [10.0, 30.0],
        )
        self.assertEqual(
            [hour["avg_rolling_queries"] for hour in repeated],
            [100.0, 200.0],
        )

    def test_additional_snapshots_are_preserved(self):
        start = datetime(
            2026, 11, 21, 10, tzinfo=timezone.utc
        )

        self.insert_rows([
            (
                (start + timedelta(minutes=i)).isoformat(),
                100,
                20,
            )
            for i in range(15)
        ])

        results = get_hourly_aggregates(
            start.isoformat(),
            (start + timedelta(hours=1)).isoformat(),
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["snapshot_count"], 15)
        self.assertEqual(results[0]["valid_blocking_samples"], 15)
        self.assertAlmostEqual(
            results[0]["avg_block_percentage"], 20.0
        )
