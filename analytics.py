from contextlib import closing
import sqlite3
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo

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


def _query_snapshot_history(start_utc, end_utc):
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
            LIMIT ?
            """,
            (start_utc, end_utc , 1001),
        ).fetchall()

    return [dict(row) for row in rows]

def get_snapshot_history(start_utc, end_utc):
    """Return up to 1000 historical DNS snapshots."""

    snapshots = _query_snapshot_history(start_utc, end_utc)

    return snapshots[:1000]


def get_hourly_aggregates(start_utc, end_utc):
    """Return hourly DNS snapshot aggregates within a UTC time range."""

    start_dt = validate_utc_timestamp(start_utc)
    end_dt = validate_utc_timestamp(end_utc)

    if start_dt >= end_dt:
        raise ValueError("Start time must be before end time")

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                SUBSTR(collected_at_utc, 1, 13)
                    || ':00:00+00:00' AS hour_start_utc,
                COUNT(*) AS snapshot_count,
                COUNT(NULLIF(total_queries, 0))
                    AS valid_blocking_samples,
                AVG(
                    100.0 * blocked_queries
                    / NULLIF(total_queries, 0)
                ) AS avg_block_percentage,
                AVG(total_queries) AS avg_rolling_queries
            FROM dns_snapshots
            WHERE collected_at_utc >= ?
              AND collected_at_utc < ?
            GROUP BY hour_start_utc
            ORDER BY hour_start_utc ASC
            """,
            (start_dt.isoformat(), end_dt.isoformat()),
        ).fetchall()

    return [dict(row) for row in rows]



def _build_heatmap_calendar(now_utc):
    """Generate seven local dates and their expected hourly intervals."""

    local_tz = ZoneInfo("America/Chicago")

    today = now_utc.astimezone(local_tz).date()
    first_date = today - timedelta(days=6)

    dates = [
        (first_date + timedelta(days=i)).isoformat()
        for i in range(7)
    ]

    start_utc = datetime.combine(
        first_date, time.min, tzinfo=local_tz
    ).astimezone(timezone.utc)

    end_utc = datetime.combine(
        today + timedelta(days=1),
        time.min,
        tzinfo=local_tz
    ).astimezone(timezone.utc)

    hours = []
    hour = start_utc

    while hour < end_utc:
        local = hour.astimezone(local_tz)
        next_hour = hour + timedelta(hours=1)

        if hour > now_utc:
            status = "future"
        elif now_utc < next_hour:
            status = "current"
        else:
            status = "elapsed"

        hours.append({
            "hour_start_utc": hour.isoformat(),
            "local_date": local.date().isoformat(),
            "local_hour": local.hour,
            "utc_offset": local.isoformat()[-6:],
            "status": status,
        })

        hour = next_hour

    return dates, start_utc, end_utc, hours


def get_dns_heatmap(now_utc=None):
    """Return seven calendar days of hourly DNS analytics."""

    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        raise ValueError("Reference time must include a timezone")

    now_utc = now_utc.astimezone(timezone.utc)

    dates, start_utc, end_utc, hours = _build_heatmap_calendar(now_utc)

    aggregates = get_hourly_aggregates(
        start_utc.isoformat(),
        min(end_utc, now_utc).isoformat()
    )

    aggregates_by_hour = {
        row["hour_start_utc"]: row
        for row in aggregates
    }

    for hour in hours:
        aggregate = aggregates_by_hour.get(hour["hour_start_utc"])

        hour.update({
            "snapshot_count": 0,
            "valid_blocking_samples": 0,
            "avg_block_percentage": None,
            "avg_rolling_queries": None,
        })

        if hour["status"] == "future":
            hour["snapshot_count"] = None
            hour["valid_blocking_samples"] = None
            continue

        if aggregate is not None:
            hour.update(aggregate)

        if hour["status"] == "elapsed":
            hour["status"] = (
                "observed" if aggregate is not None else "missing"
            )

    return {
        "timezone": "America/Chicago",
        "generated_at_utc": now_utc.isoformat(),
        "dates": dates,
        "hours": hours,
    }
