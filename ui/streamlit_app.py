# streamlit_app.py — Last Session. Display only. No classification rules.

"""One page. Laps come from normalize. Family, confidence, and reason codes come from classify. The paragraph comes from explain."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.load import fixture_paths, parse_fixture
from engines.classify import classify
from engines.explain import explain
from engines.normalize import normalize

FIXTURES_DIR = ROOT / "tests" / "fixtures"


def _date_text(payload: dict) -> str:
    for key in ("date", "started_at"):
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _cell(value: object) -> object:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if value is None:
        return ""
    return value


def _lap_rows(laps: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for index, lap in enumerate(laps, start=1):
        rows.append(
            {
                "Lap": index,
                "Distance (m)": _cell(lap.get("distance_m")),
                "Seconds": _cell(lap.get("seconds")),
                "Rest (s)": _cell(lap.get("rest_s")),
            }
        )
    return rows


def render_session(payload: dict) -> None:
    """Show one session. Labels are whatever classify returns. The paragraph is explain."""
    source = str(payload.get("source", "")).strip().lower()
    if source == "fixture":
        st.markdown("FIXTURE")

    st.markdown("**Date**")
    st.write(_date_text(payload) or "—")

    st.markdown("**Laps**")
    rows = _lap_rows(normalize(payload)["laps"])
    if rows:
        st.table(rows)
    else:
        st.write("—")

    result = classify(payload)
    st.markdown("**Family**")
    st.write(result["family"])
    st.markdown("**Confidence**")
    st.write(result["confidence"])
    st.markdown("**Reason codes**")
    codes = result.get("reason_codes") or []
    st.write(", ".join(str(code) for code in codes) if codes else "—")

    st.write(explain(result))


def selected_payload() -> dict | None:
    paths = fixture_paths(FIXTURES_DIR)
    if not paths:
        return None
    names = [path.stem for path in paths]
    selected = st.selectbox("Session", names)
    path = paths[names.index(selected)]
    return parse_fixture(path.read_text(encoding="utf-8"))


st.set_page_config(page_title="Last Session", layout="centered")
st.title("Last Session")

payload = selected_payload()
if payload is None:
    st.write("No session files.")
else:
    render_session(payload)
