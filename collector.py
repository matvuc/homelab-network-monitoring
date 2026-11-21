
from datetime import datetime, timezone
from getpass import getpass

from database import initialize_database, insert_snapshot
from pihole_client import authenticate, get_dns_summary, logout


def collect_snapshot():
    password = getpass("Pi-hole password: ")

    sid = authenticate(password)

    try:
        stats = get_dns_summary(sid)
        collected_at = datetime.now(timezone.utc).isoformat()
    finally:
        logout(sid)

    initialize_database()

    insert_snapshot(
        collected_at=collected_at,
        total_queries=stats["total_queries"],
        blocked_queries=stats["blocked_queries"],
    )

    print("DNS snapshot saved successfully.")
    print("Collected at:", collected_at)
    print("Total queries:", stats["total_queries"])
    print("Blocked queries:", stats["blocked_queries"])


if __name__ == "__main__":
    collect_snapshot()
