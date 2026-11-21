from fastapi import FastAPI, Query, HTTPException
from analytics import (
    get_recent_blocking_rates,
    get_snapshot_history,
    validate_utc_timestamp,
)
from datetime import timedelta

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/dns/blocking-rates")
def blocking_rates(limit: int = Query(default=10, ge=1, le=100)):
    return get_recent_blocking_rates(limit)

@app.get("/api/dns/history")
def snapshot_history(start_utc: str, end_utc: str):
    try:
        start_dt = validate_utc_timestamp(start_utc)
        end_dt = validate_utc_timestamp(end_utc)

        if start_dt > end_dt:
            raise ValueError("Start time cannot be after end time")

        if end_dt - start_dt > timedelta(days=30):
            raise ValueError("Time range cannot exceed 30 days")

        return get_snapshot_history(start_utc, end_utc)

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
