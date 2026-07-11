"""AfterCare API — FastAPI app factory, lifespan, CORS."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.routers import alerts, chat, patients, whatsapp
from app.seed import seed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aftercare")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db()
    async with SessionLocal() as session:
        await seed(session)
    if settings.openai_api_key.strip():
        # The Agents SDK reads OPENAI_API_KEY from the process env, not our
        # Settings object — hand it the key from .env explicitly.
        from agents import set_default_openai_key

        set_default_openai_key(settings.openai_api_key.strip())
        logger.info("Agent mode: LLM (model=%s) with deterministic fallback", settings.llm_model)
    else:
        logger.warning(
            "Agent mode: DETERMINISTIC FALLBACK ONLY — OPENAI_API_KEY is not set. "
            "Replies use the checklist keyword classifier and templates."
        )
    yield


app = FastAPI(
    title="AfterCare API",
    description="Post-discharge patient check-in agent with nurse escalation.",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted({settings.frontend_url, "http://localhost:3000"}),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(patients.router)
app.include_router(alerts.router)
app.include_router(whatsapp.router)


@app.get("/")
async def health() -> dict:
    return {"service": "AfterCare API", "status": "ok"}
