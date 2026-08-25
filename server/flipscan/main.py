"""FastAPI application — API, static PWA, and the scheduler in one process."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api import deals_router, devices_router, scans_router, settings_router
from .config import REPO_ROOT, get_settings
from .db import init_db
from .scheduler import start_scheduler, stop_scheduler

log = logging.getLogger(__name__)

WEB_DIR = REPO_ROOT / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    init_db()
    log.info("database ready")

    if not settings.api_token:
        log.warning(
            "No API token set — every API route will return 503. "
            "Run `flipscan init`."
        )

    # Opt-out rather than opt-in: the scheduler running is the normal state,
    # and a deployment that silently isn't scanning is the worst outcome here.
    if os.environ.get("FLIPSCAN_DISABLE_SCHEDULER") != "1":
        start_scheduler(settings)
    else:
        log.info("scheduler disabled by FLIPSCAN_DISABLE_SCHEDULER")

    yield

    stop_scheduler()


app = FastAPI(
    title="FlipScan",
    description=(
        "Finds underpriced resale listings near Portland, grades their "
        "condition from the photos, subtracts every real cost, and pushes "
        "the ones worth driving to."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# The PWA is served from this same origin, so CORS is only needed for local
# development against a separate dev server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000",
                   "capacitor://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deals_router)
app.include_router(settings_router)
app.include_router(devices_router)
app.include_router(scans_router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    """Unauthenticated liveness check, for uptime monitors and Docker."""
    return {"status": "ok", "version": app.version}


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/app/")


# Cached listing photos and full-page listing screenshots.
media_dir = Path(get_settings().media_dir)
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

if WEB_DIR.exists():
    @app.get("/app/{path:path}", include_in_schema=False)
    def serve_app(path: str = "") -> FileResponse:
        """Serve the PWA, falling back to index.html.

        The app routes on the URL hash, so any /app/* path is the same
        document — but a real file (the service worker, the manifest, an
        icon) has to be served as itself or installation breaks.
        """
        if path:
            candidate = (WEB_DIR / path).resolve()
            # Contain the path: a crafted `path` must not escape into the repo.
            if candidate.is_file() and str(candidate).startswith(str(WEB_DIR.resolve())):
                return FileResponse(candidate)
        return FileResponse(WEB_DIR / "index.html")

    # The service worker must be served from the origin root, not /app/, or
    # its scope won't cover the whole site and background push won't work.
    @app.get("/sw.js", include_in_schema=False)
    def service_worker() -> FileResponse:
        return FileResponse(WEB_DIR / "sw.js", media_type="application/javascript")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest() -> FileResponse:
        return FileResponse(
            WEB_DIR / "manifest.webmanifest", media_type="application/manifest+json"
        )
else:  # pragma: no cover
    log.warning("web/ not found — the phone app won't be served")
