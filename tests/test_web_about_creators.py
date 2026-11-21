# test_web_about_creators.py — About stays the Streamlit text. Creators does not name one athlete.

from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.about import about_sections
from ui.theme import ABOUT_CREDIT

ABOUT_TS = ROOT / "web" / "lib" / "about-copy.ts"
CREATORS_TS = ROOT / "web" / "lib" / "creators-copy.ts"
ABOUT_VIEW = ROOT / "web" / "components" / "AboutView.tsx"
CREATORS_VIEW = ROOT / "web" / "components" / "CreatorsView.tsx"


def about_payload() -> dict:
    """The lines page_about draws, in order, from about_sections()."""
    sections = []
    for section in about_sections():
        shown = section.get("shown")
        visible = list(shown) if isinstance(shown, list) and shown else list(section["paragraphs"])
        closing: list[str] = []
        hidden: list[str] = []
        if not shown:
            closing = list(section["closing"])
        else:
            hidden = list(section["paragraphs"]) + list(section["closing"])
        sections.append(
            {
                "title": section["title"],
                "visible": visible,
                "rows": [{"label": label, "line": line} for label, line in section["rows"]],
                "closing": closing,
                "hidden": hidden,
            }
        )
    return {
        "index": "About",
        "heading": "About",
        "credit": ABOUT_CREDIT,
        "sections": sections,
    }


def _load_ts(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    start = text.index("= ") + 2
    end = text.rindex(" as const")
    return json.loads(text[start:end])


def about_index_color() -> str:
    """The color that wins for About's index. Home's light override does not apply."""
    css = (ROOT / "ui" / "static" / "app.css").read_text(encoding="utf-8")
    color = ""
    for chunk in css.split("}"):
        if "{" not in chunk:
            continue
        selector, body = chunk.rsplit("{", 1)
        selector = " ".join(selector.split())
        if any(skip in selector for skip in ("rio-home-hero", "rio-card", "rio-mini", "rio-soft-card", "rio-daycard", "st-key-rio-home-today")):
            continue
        parts = [part.strip() for part in selector.split(",")]
        if not any(part in {".rio-index", ".rio-index-light"} for part in parts):
            continue
        for decl in body.split(";"):
            decl = decl.strip()
            if decl.startswith("color:"):
                color = decl.split(":", 1)[1].split("!")[0].strip()
    if not color:
        raise AssertionError("the About index color was not found")
    return color


def about_index_is_shown() -> bool:
    """The About banner includes the index. The orange rule is the dash in front of it."""
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    page = app[app.index("def page_about(") : app.index("\ndef page_settings(")]
    return "rio-index-light" in page and ">About</p>" in page


def next_shows_about_index(view: str) -> bool:
    banner = view[view.index("rio-about-banner") : view.index("rio-photo-credit")]
    return "rio-index" in banner


def _lines(payload: dict, *, creators: bool = False, show_index: bool = True) -> list[str]:
    if creators:
        return [
            payload["banner"],
            payload["heading"],
            payload["alt"],
            payload["name"],
            *payload["paragraphs"],
            payload["close"],
        ]
    lines = [payload["heading"], payload["credit"]]
    if show_index:
        lines.insert(0, payload["index"])
    for section in payload["sections"]:
        lines.append(section["title"])
        lines.extend(section["visible"])
        for row in section["rows"]:
            lines.append(row["label"])
            lines.append(row["line"])
        lines.extend(section["closing"])
    return lines


def _hidden(payload: dict, *, creators: bool = False) -> list[str]:
    if creators:
        return [payload["comment"]]
    lines: list[str] = []
    for section in payload["sections"]:
        lines.extend(section["hidden"])
    return lines


def _diff(name: str, expected: list[str], actual: list[str]) -> str:
    return "".join(
        difflib.unified_diff(
            [line + "\n" for line in expected],
            [line + "\n" for line in actual],
            fromfile=f"streamlit {name}",
            tofile=f"next {name}",
        )
    )


def _write_ts(path: Path, export: str, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(
        "// Generated from the Streamlit page. Do not edit the sentences.\n"
        f"export const {export} = {body} as const;\n",
        encoding="utf-8",
    )


def test_rendered_about_and_creators_text_matches_streamlit() -> None:
    """About stays the Streamlit text. Creators on the shared app does not name one athlete."""
    expected_about = about_payload()
    actual_about = _load_ts(ABOUT_TS)
    actual_creators = _load_ts(CREATORS_TS)
    about_view = ABOUT_VIEW.read_text(encoding="utf-8")
    creators_view = CREATORS_VIEW.read_text(encoding="utf-8")
    shown = about_index_is_shown()
    diff = "".join(
        (
            _diff(
                "about visible",
                _lines(expected_about, show_index=shown),
                _lines(actual_about, show_index=next_shows_about_index(about_view)),
            ),
            _diff("about hidden", _hidden(expected_about), _hidden(actual_about)),
        )
    )
    if diff:
        raise AssertionError(diff or "the rendered copy differs")
    if actual_about != expected_about:
        raise AssertionError("the copy objects differ")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    page = app[app.index("def page_about(") : app.index("\ndef page_settings(")]
    if '<p class="rio-index rio-index-light">About</p>' not in page or "<h1>About</h1>" not in page:
        raise AssertionError("the About banner moved")
    if "about_sections(" not in page or "hidden" not in page:
        raise AssertionError("About no longer keeps the long paragraphs")
    for token in (
        "section.title",
        "section.visible",
        "section.rows",
        "section.closing",
        "section.hidden",
        "row.label",
        "row.line",
        "ABOUT.heading",
        "ABOUT.credit",
    ):
        if token not in about_view:
            raise AssertionError(token)
    if shown != next_shows_about_index(about_view):
        raise AssertionError("the About eyebrow is shown on one side only")
    for token in ("CREATORS.banner", "CREATORS.heading", "CREATORS.alt", "CREATORS.name", "CREATORS.paragraphs", "CREATORS.close"):
        if token not in creators_view:
            raise AssertionError(token)
    for view in (about_view, creators_view):
        for banned in (".slice(", ".replace(", ".substring("):
            if banned in view:
                raise AssertionError(banned)
    css = (ROOT / "web" / "app" / "globals.css").read_text(encoding="utf-8")
    about_css = css[css.index(".page-about, .page-creators") :]
    if "/photos/about" not in about_css or "chase-blocks" in about_view:
        raise AssertionError("About is using the wrong photo")
    if about_css.index("/photos/about") > about_css.index(".page-creators .rio-hero"):
        raise AssertionError("the About photo is not on the About banner")
    if "/photos/startup-track" not in creators_view or "chase-blocks" in creators_view:
        raise AssertionError("Creators is using the wrong photo")
    if "Photo by Giant Asparagus on Pexels" not in creators_view:
        raise AssertionError("Creators dropped the track photo credit")
    visible = "\n".join(_lines(actual_creators, creators=True))
    for banned in ("Chase", "Jay Rose", "Jay", "Bentley", "Stanford", "1:55", "chasejrose", "Editable placeholder", "Bio coming soon"):
        if banned in visible or banned in creators_view:
            raise AssertionError(banned)
    if "comment" in actual_creators:
        raise AssertionError("the shared creators page still keeps a hidden bio")
    hidden = "\n".join(_hidden(actual_about))
    shown = "\n".join(_lines(actual_about))
    if "Those calls stop once recorded spend reaches $25." not in hidden:
        raise AssertionError("the $25 sentence was dropped")
    if "$25" in shown:
        raise AssertionError("the $25 sentence is in the visible About text")


def main() -> None:
    if "--write" in sys.argv:
        _write_ts(ABOUT_TS, "ABOUT", about_payload())
        print("wrote about copy")
        return
    test_rendered_about_and_creators_text_matches_streamlit()
    print("about creators copy ok")


if __name__ == "__main__":
    main()
