
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        test_db_path = Path(self.temp_dir.name) / "test.db"

        patcher = patch.object(database, "DB_PATH", test_db_path)
        patcher.start()
        self.addCleanup(patcher.stop)

        database.initialize_database()

    def test_insert_valid_snapshot(self):
        database.insert_snapshot(
            "2026-11-21T10:00:00+00:00",
            100,
            25
        )

        snapshots = database.get_snapshots()

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0][2], 100)
        self.assertEqual(snapshots[0][3], 25)

    def test_reject_invalid_snapshot(self):
        with self.assertRaises(database.sqlite3.IntegrityError):
            database.insert_snapshot(
                "2026-11-21T10:05:00+00:00",
                100,
                150
            )

        snapshots = database.get_snapshots()

        self.assertEqual(len(snapshots), 0)

    def test_snapshots_ordered_newest_first(self):
        database.insert_snapshot(
            "2026-11-21T10:00:00+00:00",
            100,
            20
        )

        database.insert_snapshot(
            "2026-11-21T09:00:00+00:00",
            80,
            10
        )

        database.insert_snapshot(
            "2026-11-21T11:00:00+00:00",
            150,
            30
        )

        snapshots = database.get_snapshots()

        timestamps = [row[1] for row in snapshots]

        self.assertEqual(
            timestamps,
            [
                "2026-11-21T11:00:00+00:00",
                "2026-11-21T10:00:00+00:00",
                "2026-11-21T09:00:00+00:00"
            ]
        )



if __name__ == "__main__":
    unittest.main()
