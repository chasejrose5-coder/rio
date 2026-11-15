# test_live_origin.py — the docs name www.riorunning.com and keep the old hosts.

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE = "https://www.riorunning.com"
OLD = (
    "https://riotraining.streamlit.app",
    "https://rio-one-mocha.vercel.app",
    "https://rio-rio-44fa.vercel.app",
)


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_the_named_docs_use_the_live_origin() -> None:
    docs = (
        "docs/email-setup.md",
        "docs/migration/deploy-test.md",
        "docs/migration/api-contract.md",
        "docs/migration/parity-checklist.md",
        "docs/migration/parity-audit.md",
        "supabase/migrations/README.md",
        "api/README.md",
        "web/README.md",
    )
    for path in docs:
        if LIVE not in _text(path):
            raise AssertionError(path)


def test_old_hosts_stay_on_the_redirect_lists() -> None:
    for path in (
        "docs/email-setup.md",
        "docs/migration/deploy-test.md",
        "supabase/migrations/README.md",
    ):
        text = _text(path)
        if "Leave" not in text:
            raise AssertionError(path + " does not say to leave the old URLs")
        for old in OLD:
            if old not in text:
                raise AssertionError(path + " dropped " + old)
        if "https://www.riorunning.com/confirm" not in text:
            raise AssertionError(path + " is missing the confirm redirect")
        if "https://www.riorunning.com/reset-password" not in text:
            raise AssertionError(path + " is missing the reset redirect")


def test_signup_mail_is_confirm_and_strava_is_www() -> None:
    readme = _text("api/README.md")
    if "confirmation link is `{RIO_FRONTEND_ORIGIN}/confirm`" not in readme:
        raise AssertionError("api/README.md still has the old signup path")
    if "`{RIO_FRONTEND_ORIGIN}/`" in readme:
        raise AssertionError("api/README.md still sends signup mail to /")
    migrations = _text("supabase/migrations/README.md")
    if "https://www.riorunning.com/confirm" not in migrations:
        raise AssertionError("the migrations note still sends signup mail to /")
    if "www.riorunning.com" not in migrations:
        raise AssertionError("the migrations note is missing the Strava domain")
    deploy = _text("docs/migration/deploy-test.md")
    if "www.riorunning.com" not in deploy:
        raise AssertionError("deploy-test.md is missing the Strava domain")
    if "RIO_FRONTEND_ORIGIN" not in deploy or "RIO_CALLBACK_BASE_URL" not in deploy:
        raise AssertionError("deploy-test.md dropped the Render names")
    if "`https://www.riorunning.com`" not in deploy:
        raise AssertionError("Render is not pointed at the live origin")
