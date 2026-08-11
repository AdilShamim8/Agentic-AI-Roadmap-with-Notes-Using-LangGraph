"""FastAPI entrypoint — Agent-as-a-Service Platform backend."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import Base
from routers import (
    agents_router,
    auth_router,
    billing_router,
    health_router,
    internal_router,
    invocations_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("a2a.platform")

app = FastAPI(
    title="Agent-as-a-Service Platform",
    description=(
        "A marketplace for deploying, discovering, and invoking AI agents "
        "via the A2A (Agent-to-Agent) protocol."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(invocations_router)
app.include_router(billing_router)
app.include_router(internal_router)


@app.on_event("startup")
async def startup() -> None:
    logger.info("A2A Platform backend starting up")
    logger.info("Database: %s", settings.database_url.split("@")[-1])
    logger.info("CORS origins: %s", settings.cors_origins_list)
    logger.info("Stripe configured: %s", bool(settings.stripe_secret_key))


@app.get("/")
async def root() -> dict:
    return {
        "service": "Agent-as-a-Service Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
