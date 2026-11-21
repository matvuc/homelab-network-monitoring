
import unittest
from unittest.mock import patch

import collector


class TestCollector(unittest.TestCase):

    @patch("collector.insert_snapshot")
    @patch("collector.initialize_database")
    @patch("collector.logout")
    @patch("collector.get_dns_summary")
    @patch("collector.authenticate")
    @patch("collector.load_password")
    def test_collect_snapshot_success(
        self,
        mock_password,
        mock_authenticate,
        mock_summary,
        mock_logout,
        mock_initialize,
        mock_insert,
    ):
        mock_password.return_value = "fake-password"
        mock_authenticate.return_value = "fake-session-123"

        mock_summary.return_value = {
            "total_queries": 1000,
            "blocked_queries": 250,
            "percent_blocked": 25.0,
        }

        collector.collect_snapshot()

        mock_authenticate.assert_called_once_with("fake-password")
        mock_summary.assert_called_once_with("fake-session-123")
        mock_logout.assert_called_once_with("fake-session-123")
        mock_initialize.assert_called_once()
        mock_insert.assert_called_once()

        saved_data = mock_insert.call_args.kwargs

        self.assertEqual(saved_data["total_queries"], 1000)
        self.assertEqual(saved_data["blocked_queries"], 250)
        self.assertIsInstance(saved_data["collected_at"], str)

    @patch("collector.insert_snapshot")
    @patch("collector.initialize_database")
    @patch("collector.logout")
    @patch("collector.get_dns_summary")
    @patch("collector.authenticate")
    @patch("collector.load_password")
    def test_collect_snapshot_failure_logs_out(
        self,
        mock_password,
        mock_authenticate,
        mock_summary,
        mock_logout,
        mock_initialize,
        mock_insert,
    ):
        mock_password.return_value = "fake-password"
        mock_authenticate.return_value = "fake-session-123"

        mock_summary.side_effect = ConnectionError(
            "Pi-hole unavailable"
        )

        with self.assertRaises(ConnectionError):
            collector.collect_snapshot()

        mock_logout.assert_called_once_with("fake-session-123")
        mock_initialize.assert_not_called()
        mock_insert.assert_not_called()


    @patch("collector.logger")
    @patch("collector.insert_snapshot")
    @patch("collector.initialize_database")
    @patch("collector.logout")
    @patch("collector.get_dns_summary")
    @patch("collector.authenticate")
    @patch("collector.load_password")
    def test_collect_snapshot_database_failure(
        self,
        mock_password,
        mock_authenticate,
        mock_summary,
        mock_logout,
        mock_initialize,
        mock_insert,
        mock_logger,
    ):
        mock_password.return_value = "fake-password"
        mock_authenticate.return_value = "fake-session-123"

        mock_summary.return_value = {
            "total_queries": 1000,
            "blocked_queries": 250,
            "percent_blocked": 25.0,
        }

        mock_insert.side_effect = OSError("Disk is full")

        with self.assertRaises(OSError):
            collector.collect_snapshot()

        mock_logout.assert_called_once_with("fake-session-123")
        mock_initialize.assert_called_once()
        mock_insert.assert_called_once()
        mock_logger.info.assert_not_called()


    @patch("collector.insert_snapshot")
    @patch("collector.initialize_database")
    @patch("collector.logout")
    @patch("collector.get_dns_summary")
    @patch("collector.authenticate")
    @patch("collector.load_password")
    def test_collect_snapshot_authentication_failure(
        self,
        mock_password,
        mock_authenticate,
        mock_summary,
        mock_logout,
        mock_initialize,
        mock_insert,
    ):
        mock_password.return_value = "fake-password"

        mock_authenticate.side_effect = RuntimeError(
            "Pi-hole authentication failed"
        )

        with self.assertRaises(RuntimeError) as error:
            collector.collect_snapshot()

        self.assertEqual(
            str(error.exception),
            "Pi-hole authentication failed"
        )

        mock_summary.assert_not_called()
        mock_logout.assert_not_called()
        mock_initialize.assert_not_called()
        mock_insert.assert_not_called()
