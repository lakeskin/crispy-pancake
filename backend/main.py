"""
SalikChat Backend — FastAPI Application
Connect car owners with mechanics for quick diagnostics.
"""

import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
# Silence noisy HTTP-level loggers
for _noisy in ("hpack", "httpcore", "httpx", "h2"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)
logger = logging.getLogger("salikchat")

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)
logger.info("Loaded .env from %s (exists=%s)", env_path, env_path.exists())

# Load YAML config
config_path = Path(__file__).resolve().parent / "config.yaml"
with open(config_path, "r", encoding="utf-8") as f:
    APP_CONFIG = yaml.safe_load(f)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    logger.info("🚗 SalikChat backend starting …")
    yield
    logger.info("🛑 SalikChat backend shutting down …")


app = FastAPI(
    title=APP_CONFIG["app"]["name"],
    version=APP_CONFIG["app"]["version"],
    description=APP_CONFIG["app"]["description"],
    lifespan=lifespan,
)

# ── Global exception handler (ensures CORS headers even on 500) ─
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


# ── Request logging middleware ─
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("→ %s %s", request.method, request.url.path)
    response = await call_next(request)
    logger.info("← %s %s  %s", request.method, request.url.path, response.status_code)
    return response


# ---------- CORS ----------
# NOTE: CORSMiddleware must be added AFTER other middleware so it wraps outermost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Routers ----------
from routes.auth import router as auth_router          # noqa: E402
from routes.profiles import router as profiles_router  # noqa: E402
from routes.issues import router as issues_router      # noqa: E402
from routes.responses import router as responses_router  # noqa: E402
from routes.conversations import router as conversations_router  # noqa: E402
from routes.messages import router as messages_router  # noqa: E402
from routes.config_routes import router as config_router  # noqa: E402
from routes.uploads import router as uploads_router  # noqa: E402

app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(issues_router)
app.include_router(responses_router)
app.include_router(conversations_router)
app.include_router(messages_router)
app.include_router(config_router)
app.include_router(uploads_router)


# ---------- Health ----------
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "salikchat"}
