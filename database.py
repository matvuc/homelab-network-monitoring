import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "analytics.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def initialize_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        with open(SCHEMA_PATH, "r") as file:
            connection.executescript(file.read())

    print("Database initialized successfully.")

def insert_snapshot(collected_at, total_queries, blocked_queries):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO dns_snapshots (
                collected_at_utc,
                total_queries,
                blocked_queries
            )
            VALUES (?, ?, ?)
            """,
            (collected_at, total_queries, blocked_queries)
        )

def get_snapshots():
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            SELECT
                id,
                collected_at_utc,
                total_queries,
                blocked_queries
            FROM dns_snapshots
            ORDER BY collected_at_utc DESC
            """
        )

        return cursor.fetchall()
