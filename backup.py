import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DB = BASE_DIR / "data" / "analytics.db"
BACKUP_DIR = BASE_DIR / "backups"


def create_backup():
    if not SOURCE_DB.is_file():
        raise FileNotFoundError(f"Database not found: {SOURCE_DB}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = BACKUP_DIR / f"analytics-{timestamp}.db"

    try:
        with closing(sqlite3.connect(
            f"file:{SOURCE_DB}?mode=ro", uri=True
        )) as source:
            with closing(sqlite3.connect(destination)) as backup:
                source.backup(backup)

                integrity = backup.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(f"Backup integrity failed: {integrity}")

        print(f"Backup created: {destination.name}")
        print(f"Integrity check: {integrity}")

    except Exception:
        destination.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    create_backup()
