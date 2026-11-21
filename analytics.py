from contextlib import closing
import sqlite3
from datetime import datetime, timezone

from database import DB_PATH


def get_recent_blocking_rates(limit=10):
    """Return recent DNS snapshots with blocking percentages."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                collected_at_utc,
                total_queries,
                blocked_queries,
                ROUND(
                    blocked_queries * 100.0
                    / NULLIF(total_queries, 0),
                    2
                ) AS block_percentage
            FROM dns_snapshots
            ORDER BY collected_at_utc DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def validate_utc_timestamp(value):
    """Validate and normalize an ISO 8601 UTC timestamp."""

    if not isinstance(value, str):
        raise ValueError("Timestamp must be a string")

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Invalid ISO 8601 timestamp") from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")

    return parsed.astimezone(timezone.utc)


def get_snapshot_history(start_utc, end_utc):
    """Return DNS snapshots within a UTC time range."""

    start_dt = validate_utc_timestamp(start_utc)
    end_dt = validate_utc_timestamp(end_utc)

    if start_dt > end_dt:
        raise ValueError("Start time cannot be after end time")

    start_utc = start_dt.isoformat()
    end_utc = end_dt.isoformat()

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                collected_at_utc,
                total_queries,
                blocked_queries,
                ROUND(
                    blocked_queries * 100.0
                    / NULLIF(total_queries, 0),
                    2
                ) AS block_percentage
            FROM dns_snapshots
            WHERE collected_at_utc >= ?
              AND collected_at_utc <= ?
            ORDER BY collected_at_utc ASC
            """,
            (start_utc, end_utc),
        ).fetchall()

    return [dict(row) for row in rows]
