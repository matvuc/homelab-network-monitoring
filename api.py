from fastapi import FastAPI, Query
from analytics import get_recent_blocking_rates


app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/dns/blocking-rates")
def blocking_rates(limit: int = Query(default=10, ge=1, le=100)):
    return get_recent_blocking_rates(limit)
