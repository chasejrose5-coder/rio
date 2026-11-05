# test_review_ops.py — sealed session tokens and the dependency pin.

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.cloud_store import open_session_secret, seal_session_secret


def test_a_session_secret_round_trips_and_plaintext_still_opens() -> None:
    previous = os.environ.get("RIO_SESSION_KEY")
    os.environ["RIO_SESSION_KEY"] = "test-session-key"
    try:
        sealed = seal_session_secret("refresh-1")
        if sealed == "refresh-1" or not sealed.startswith("f2."):
            raise AssertionError(sealed)
        if open_session_secret(sealed) != "refresh-1":
            raise AssertionError("the sealed token did not open")
        if "refresh-1" in sealed:
            raise AssertionError("the token was still readable")
    finally:
        if previous is None:
            os.environ.pop("RIO_SESSION_KEY", None)
        else:
            os.environ["RIO_SESSION_KEY"] = previous
    if open_session_secret("refresh-1") != "refresh-1":
        raise AssertionError("an older plaintext row stopped opening")


def test_cryptography_pin_is_past_the_advisories() -> None:
    pinned = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    live = "\n".join(
        line for line in pinned.splitlines() if line.strip() and not line.strip().startswith("#")
    )
    if "cryptography==50.0.0" not in live or "cryptography==44.0.2" in live:
        raise AssertionError(live)
    import cryptography

    major = int(cryptography.__version__.split(".", 1)[0])
    if major < 50:
        raise AssertionError(cryptography.__version__)


def main() -> None:
    test_a_session_secret_round_trips_and_plaintext_still_opens()
    test_cryptography_pin_is_past_the_advisories()
    print("review ops ok")


if __name__ == "__main__":
    main()
