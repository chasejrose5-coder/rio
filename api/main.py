# main.py — the FastAPI app. Streamlit stays the live site.

"""Run with uvicorn from the repository root.

The engines and the season services are imported. They are not copied.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.account_routes import router as account_router
from api.admin_routes import router as admin_router
from api.errors import ApiError
from api.fixture_routes import router as fixture_router
from api.insight_routes import router as insight_router
from api.routes import auth_router, health_router, season_router
from api.screen_routes import router as screen_router
from api.settings import load_settings
from api.strava_routes import router as strava_router
from ui.accounts import accounts_path
from ui.activities import load_local_env
from ui.cloud_config import cloud_settings
from ui.cloud_store import SupabaseDirectory


def create_app(
    *,
    directory=None,
    accounts: Path | None = None,
    frontend_origin: str | None = None,
    load_env: bool = True,
) -> FastAPI:
    """One app. Pass a directory in tests. None uses the local account file.

    Production calls this with the Supabase directory when the environment
    has a URL and an anon key, and with None when it does not.
    """
    if load_env:
        load_local_env()
    settings = load_settings(frontend_origin)
    app = FastAPI(title="RIO", docs_url="/docs", redoc_url=None)
    app.state.settings = settings
    app.state.directory = directory
    app.state.accounts_path = accounts if accounts is not None else accounts_path()
    app.state.local_sessions = {}
    app.state.oauth_nonces = {}
    app.state.insight_jobs = {}
    app.state.insight_dates = {}
    from ui.strava import RateGate
    from ui.strava_store import MemoryStrava

    app.state.memory_strava = MemoryStrava()
    app.state.strava_service_key = "memory-service"
    app.state.strava_gate = RateGate()
    app.state.strava_post = None
    app.state.strava_get = None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "If-Match", "X-RIO-Response"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(account_router)
    app.include_router(season_router)
    app.include_router(admin_router)
    app.include_router(fixture_router)
    app.include_router(strava_router)
    app.include_router(insight_router)
    app.include_router(screen_router)

    @app.exception_handler(ApiError)
    def _api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content={"detail": exc.message})

    return app


def directory_from_env():
    """The hosted directory, or None so sign-in uses the local account file."""
    found = cloud_settings()
    if found is None:
        return None
    return SupabaseDirectory(found["url"], found["anon_key"], found["service_key"])


app = create_app(directory=directory_from_env())
