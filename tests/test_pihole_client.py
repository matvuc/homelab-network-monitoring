from urllib.error import HTTPError, URLError
import io
import json
import unittest
from unittest.mock import patch

import pihole_client


class TestPiHoleClient(unittest.TestCase):

    @patch("pihole_client.create_ssl_context")
    @patch("pihole_client.urlopen")
    def test_authenticate_success(self, mock_urlopen, mock_ssl):
        fake_response = {
            "session": {
                "valid": True,
                "sid": "test-session-123"
            }
        }

        response_bytes = json.dumps(fake_response).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(
            response_bytes
        )

        sid = pihole_client.authenticate("fake-password")

        self.assertEqual(sid, "test-session-123")

    @patch("pihole_client.create_ssl_context")
    @patch("pihole_client.urlopen")
    def test_authenticate_failure(self, mock_urlopen, mock_ssl):
        fake_response = {
            "session": {
                "valid": False,
                "sid": None
            }
        }

        response_bytes = json.dumps(fake_response).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(
            response_bytes
        )

        with self.assertRaises(RuntimeError) as error:
            pihole_client.authenticate("wrong-password")

        self.assertEqual(
            str(error.exception),
            "Pi-hole authentication failed"
        )


    @patch("pihole_client.create_ssl_context")
    @patch("pihole_client.urlopen")
    def test_get_dns_summary_success(self, mock_urlopen, mock_ssl):
        fake_response = {
            "queries": {
                "total": 1000,
                "blocked": 250,
                "percent_blocked": 25.0
            }
        }

        response_bytes = json.dumps(fake_response).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(
            response_bytes
        )

        result = pihole_client.get_dns_summary("test-session-123")

        self.assertEqual(result["total_queries"], 1000)
        self.assertEqual(result["blocked_queries"], 250)
        self.assertEqual(result["percent_blocked"], 25.0)


    @patch("pihole_client.create_ssl_context")
    @patch("pihole_client.urlopen")
    def test_get_dns_summary_http_error(self, mock_urlopen, mock_ssl):
        mock_urlopen.side_effect = HTTPError(
            url="https://pi.hole/api/stats/summary",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=None,
        )

        with self.assertRaises(HTTPError) as error:
            pihole_client.get_dns_summary("test-session-123")

        self.assertEqual(error.exception.code, 500)


    @patch("pihole_client.create_ssl_context")
    @patch("pihole_client.urlopen")
    def test_get_dns_summary_invalid_json(self, mock_urlopen, mock_ssl):
        invalid_json = b'{"queries": {"total": 1000, "blocked":'

        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(
            invalid_json
        )

        with self.assertRaises(json.JSONDecodeError):
            pihole_client.get_dns_summary("test-session-123")


    @patch("pihole_client.create_ssl_context")
    @patch("pihole_client.urlopen")
    def test_get_dns_summary_missing_field(self, mock_urlopen, mock_ssl):
        fake_response = {
            "queries": {
                "total": 1000,
                "blocked": 250
            }
        }

        response_bytes = json.dumps(fake_response).encode("utf-8")

        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(
            response_bytes
        )

        with self.assertRaises(KeyError) as error:
            pihole_client.get_dns_summary("test-session-123")

        self.assertEqual(str(error.exception), "'percent_blocked'")


    @patch("pihole_client.create_ssl_context")
    @patch("pihole_client.urlopen")
    def test_get_dns_summary_network_error(self, mock_urlopen, mock_ssl):
        mock_urlopen.side_effect = URLError(
            "Connection refused"
        )

        with self.assertRaises(URLError) as error:
            pihole_client.get_dns_summary("test-session-123")

        self.assertEqual(
            str(error.exception.reason),
            "Connection refused"
        )


    @patch("pihole_client.create_ssl_context")
    @patch("pihole_client.urlopen")
    def test_logout_sends_delete_request(self, mock_urlopen, mock_ssl):
        sid = "test-session-123"

        pihole_client.logout(sid)

        mock_urlopen.assert_called_once()

        request = mock_urlopen.call_args.args[0]

        self.assertEqual(request.get_method(), "DELETE")
        self.assertEqual(
            request.get_header("X-ftl-sid"),
            sid
        )
