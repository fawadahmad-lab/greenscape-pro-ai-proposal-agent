"""FastAPI application entrypoint for the Greenscape Pro proposal copilot."""

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import proposals
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.seed.pricing_catalog import seed_pricing_catalog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and seed demo pricing on startup."""
    logger.info("Creating database tables if needed...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        added = seed_pricing_catalog(db)
        logger.info("Pricing catalog seeded (added=%s).", added)
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: restricted to configured origins (no wildcard in production).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proposals.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
