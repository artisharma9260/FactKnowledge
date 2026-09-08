"""
Fact Knowledge Layer — FastAPI Application Entry Point
"""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Must run BEFORE importing anything that reads env vars at import time
# (fact_extractor.py and embeddings.py read GEMINI_API_KEY at module load).
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routes import documents, facts, relationships

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database on startup."""
    logger.info("Initializing database …")
    await init_db()
    logger.info("Database ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Fact Knowledge Layer",
    description="Extract, ground, and cross-reference facts from PDF documents.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(facts.router, prefix="/facts", tags=["Facts"])
app.include_router(relationships.router, prefix="/relationships", tags=["Relationships"])


@app.get("/health")
async def health():
    return {"status": "ok"}
