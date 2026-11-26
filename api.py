from fastapi import FastAPI, Query, HTTPException
from analytics import (
    get_recent_blocking_rates,
    get_snapshot_history,
    get_dns_heatmap,
    validate_utc_timestamp,
)
from datetime import timedelta

from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)

@app.get("/dashboard")
def dashboard():
    return FileResponse(FRONTEND_DIR / "index.html")

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



@app.get("/api/dns/heatmap")
def dns_heatmap():
    """Return seven calendar days of hourly DNS analytics."""
    return get_dns_heatmap()
