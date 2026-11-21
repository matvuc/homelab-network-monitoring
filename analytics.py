from contextlib import closing
import sqlite3

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
