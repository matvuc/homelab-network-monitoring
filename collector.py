
from datetime import datetime, timezone
from  urllib.error import HTTPError
from database import initialize_database, insert_snapshot
from pihole_client import authenticate, get_dns_summary, logout
import logging

from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "collector.log"),
    ],
)

logger = logging.getLogger(__name__)

ENV_PATH = Path(__file__).resolve().parent / ".env"


def load_password():
    with open(ENV_PATH, "r") as file:
        for line in file:
            if line.startswith("PIHOLE_PASSWORD="):
                return line.removeprefix("PIHOLE_PASSWORD=").rstrip("\r\n")

    raise RuntimeError("PIHOLE_PASSWORD not found in .env")

def collect_snapshot():
    password = load_password()

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

    logger.info("DNS snapshot saved successfully.")
    print("Collected at:", collected_at)
    print("Total queries:", stats["total_queries"])
    print("Blocked queries:", stats["blocked_queries"])



if __name__ == "__main__":
    try:
        collect_snapshot()

    except HTTPError as error:
        logger.error(
            "Pi-hole API returned HTTP status %s",
            error.code
        )
        raise SystemExit(1)

    except Exception as error:
        logger.error(
            "DNS collection failed: %s",
            type(error).__name__
        )
        raise SystemExit(1)
