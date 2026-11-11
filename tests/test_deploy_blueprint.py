# test_deploy_blueprint.py — the test-deploy blueprint names hosts, not secrets.

"""render.yaml is the Render API service. GET /health is already the check.

No disk. No secret values. The checklist names every variable in the file.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _yaml() -> str:
    return (ROOT / "render.yaml").read_text(encoding="utf-8")


def _keys(text: str) -> list[str]:
    return re.findall(r"(?m)^ +\- key: ([A-Z0-9_]+)$", text)


def test_blueprint_is_a_free_api_service_with_the_health_check() -> None:
    text = _yaml()
    if "type: web" not in text or "runtime: python" not in text or "plan: free" not in text:
        raise AssertionError("the blueprint is not a free Python web service")
    if "healthCheckPath: /health" not in text:
        raise AssertionError(text)
    route = (ROOT / "api" / "routes.py").read_text(encoding="utf-8")
    if '@health_router.get("/health")' not in route or 'return {"ok": True}' not in route:
        raise AssertionError("GET /health is not the open check Render is pointed at")
    if "pip install -r requirements.txt -r api/requirements.txt" not in text:
        raise AssertionError("the build does not install both requirement files")
    if "uvicorn api.main:app --host 0.0.0.0 --port $PORT" not in text:
        raise AssertionError("the start command does not bind Render's port")
    if re.search(r"(?m)^ *disk:", text):
        raise AssertionError("a persistent disk was added")
    if "rootDir:" in text:
        raise AssertionError("rootDir would hide the repository root the API imports")


def test_blueprint_has_names_and_no_secret_values() -> None:
    text = _yaml()
    keys = _keys(text)
    required = [
        "PYTHON_VERSION",
        "RIO_SUPABASE_URL",
        "RIO_SUPABASE_ANON_KEY",
        "RIO_SUPABASE_SERVICE_ROLE_KEY",
        "RIO_FRONTEND_ORIGIN",
        "RIO_CALLBACK_BASE_URL",
        "RIO_ADMIN_EMAIL",
        "RIO_STRAVA_CLIENT_ID",
        "RIO_STRAVA_CLIENT_SECRET",
        "RIO_EXPLAIN_API_KEY",
        "RIO_EXPLAIN_MODEL",
        "RIO_EXPLAIN_BASE_URL",
        "RIO_EXPLAIN_INPUT_USD_PER_MILLION",
        "RIO_EXPLAIN_OUTPUT_USD_PER_MILLION",
        "RIO_INTERVALS_API_KEY",
        "RIO_INTERVALS_ATHLETE_ID",
    ]
    if keys != required:
        raise AssertionError(keys)
    for left_out in (
        "RIO_HERO_PATH",
        "RIO_EXPLAIN_SPEND_PATH",
        "RIO_ACCOUNTS_PATH",
        "RIO_SESSION_KEY",
        "RIO_APP_URL",
        "RIO_STRAVA_REDIRECT_URI",
        "NEXT_PUBLIC_RIO_API_URL",
        "RIO_API_ORIGIN",
    ):
        if left_out in text:
            raise AssertionError(left_out)
    values = re.findall(r"(?m)^ +value: +(.+)$", text)
    if values != ['"3.12.11"']:
        raise AssertionError(values)
    lowered = text.lower()
    for banned in ("eyj", "supabase.co", "sk-", "begin ", "password"):
        if banned in lowered:
            raise AssertionError(banned)


def test_checklist_names_every_blueprint_variable_and_the_proxy() -> None:
    doc = (ROOT / "docs" / "migration" / "deploy-test.md").read_text(encoding="utf-8")
    for key in _keys(_yaml()):
        if key not in doc:
            raise AssertionError(key)
    for name in (
        "NEXT_PUBLIC_RIO_API_URL",
        "RIO_API_ORIGIN",
        "RIO_HERO_PATH",
        "RIO_EXPLAIN_SPEND_PATH",
        "GET /health",
        "009_season_state.sql",
        "010_strava_oauth.sql",
        "011_explain_spend.sql",
        "riotraining.streamlit.app",
        "/reset-password",
        "/strava/callback",
    ):
        if name not in doc:
            raise AssertionError(name)
    if "select" not in doc.lower():
        raise AssertionError("the read-only check query is missing")
