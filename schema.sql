
CREATE TABLE IF NOT EXISTS dns_snapshots (
    id INTEGER PRIMARY KEY,
    collected_at_utc TEXT NOT NULL UNIQUE,
    total_queries INTEGER NOT NULL
        CHECK (total_queries >= 0),
    blocked_queries INTEGER NOT NULL
        CHECK (
            blocked_queries >= 0
            AND blocked_queries <= total_queries
        )
);
