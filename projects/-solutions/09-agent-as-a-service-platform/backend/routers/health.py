"""Health & metrics endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest, Gauge
from sqlalchemy import text

from database import SessionLocal

router = APIRouter(tags=["health"])

# Prometheus metrics
PLATFORM_INFO = Gauge(
    "a2a_platform_info",
    "Platform metadata",
    ["version"],
)
PLATFORM_INFO.labels(version="1.0.0").set(1)

DB_UP = Gauge("a2a_db_up", "1 if Postgres is reachable")


@router.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/ready")
async def readiness() -> dict:
    """Readiness probe — checks DB connectivity."""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        DB_UP.set(1)
        return {"status": "ready", "database": "up"}
    except Exception as e:  # noqa: BLE001
        DB_UP.set(0)
        return {"status": "not ready", "database": "down", "error": str(e)}


@router.get("/metrics")
async def metrics():
    """Prometheus scrape endpoint."""
    from fastapi.responses import Response

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
