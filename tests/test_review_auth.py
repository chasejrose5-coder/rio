# test_review_auth.py — each Google attempt keeps its own verifier.

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.cloud_store import (
    SupabaseDirectory,
    pkce_challenge,
    stash_verifier,
    take_verifier,
)


def test_two_google_attempts_keep_two_verifiers() -> None:
    directory = SupabaseDirectory("https://example.supabase.co", "anon", "svc")
    first = directory.google_url("https://riotraining.streamlit.app/")
    second = directory.google_url("https://riotraining.streamlit.app/")
    if first == second or "code_challenge=" not in first or "code_challenge=" not in second:
        raise AssertionError("the two sign-ins shared one link")
    if "flow%3D" not in first or "flow%3D" not in second:
        raise AssertionError((first, second))
    from urllib.parse import parse_qs, unquote, urlparse

    back_a = unquote(parse_qs(urlparse(first).query)["redirect_to"][0])
    back_b = unquote(parse_qs(urlparse(second).query)["redirect_to"][0])
    flow_a = parse_qs(urlparse(back_a).query)["flow"][0]
    flow_b = parse_qs(urlparse(back_b).query)["flow"][0]
    if flow_a == flow_b:
        raise AssertionError("one flow id was reused")
    kept = take_verifier(flow_a)
    other = take_verifier(flow_b)
    if not kept or not other or kept == other:
        raise AssertionError("one verifier was overwritten")
    challenge = parse_qs(urlparse(first).query)["code_challenge"][0]
    if challenge != pkce_challenge(kept):
        raise AssertionError("the link was not this attempt's challenge")
    if take_verifier(flow_a):
        raise AssertionError("a used verifier still worked")


def test_an_old_verifier_expires() -> None:
    stash_verifier("old-flow", "verifier-old", now=time.time() - 1000)
    if take_verifier("old-flow"):
        raise AssertionError("an expired sign-in still exchanged")


def test_reset_link_is_not_a_google_code() -> None:
    ui = (ROOT / "ui" / "cloud_ui.py").read_text(encoding="utf-8")
    callback = ui[ui.index("def _consume_callback(") : ui.index("def _render_sign_in(")]
    reset_at = callback.index('params.get("reset") == "password"')
    exchange_at = callback.index("exchange_code(")
    if reset_at > exchange_at:
        raise AssertionError("a reset link is still exchanged as a sign-in")
    if "token_hash" not in ui or "verify_otp" not in (ROOT / "ui" / "cloud_store.py").read_text(encoding="utf-8"):
        raise AssertionError("reset still calls set_session on the email code")
    if 'params.get("flow")' not in callback:
        raise AssertionError("the return does not name its own attempt")


def main() -> None:
    test_two_google_attempts_keep_two_verifiers()
    test_an_old_verifier_expires()
    test_reset_link_is_not_a_google_code()
    print("review auth ok")


if __name__ == "__main__":
    main()
