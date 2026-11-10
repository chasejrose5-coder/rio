# test_web_about_creators.py — Next renders the Streamlit About and Creators text.

from __future__ import annotations

import ast
import difflib
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.about import about_sections
from ui.creators import CREATORS
from ui.theme import ABOUT_CREDIT

ABOUT_TS = ROOT / "web" / "lib" / "about-copy.ts"
CREATORS_TS = ROOT / "web" / "lib" / "creators-copy.ts"
ABOUT_VIEW = ROOT / "web" / "components" / "AboutView.tsx"
CREATORS_VIEW = ROOT / "web" / "components" / "CreatorsView.tsx"


def _assign(fn: ast.FunctionDef, name: str) -> ast.AST | None:
    for stmt in fn.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name) and target.id == name:
                return stmt.value
    return None


def _function(source: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(name)


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


def _creators_parts() -> tuple[str, str, str, str, str, list[str], str]:
    """Pull the Creators literals out of page_creators. Nothing here is retyped."""
    source = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    fn = _function(source, "page_creators")
    paragraphs_node = _assign(fn, "paragraphs")
    bio_node = _assign(fn, "bio")
    if not isinstance(paragraphs_node, ast.Tuple) or not isinstance(bio_node, ast.Constant):
        raise AssertionError("the creators paragraphs moved")
    paragraphs = [elt.value for elt in paragraphs_node.elts]
    bio = bio_node.value
    if not isinstance(bio, str) or any(not isinstance(part, str) for part in paragraphs):
        raise AssertionError("a creators sentence is not text")
    heading = ""
    banner = ""
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_page_hero":
            heading = node.args[0].value
            banner = node.args[1].value
    alt = ""
    comment_prefix = ""
    for node in ast.walk(fn):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and 'alt="' in node.value:
            start = node.value.index('alt="') + len('alt="')
            alt = node.value[start : node.value.index('"', start)]
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "rio-creator-kept" in node.value:
            comment_prefix = node.value[node.value.index("<!--") :]
    if not heading or not banner or not alt or not comment_prefix:
        raise AssertionError("a creators label moved")
    kept = "".join(
        f"<p>{escape(str(person['role']), quote=True)}. "
        f"{escape(str(person['name']), quote=True)}. "
        f"{escape(str(person['bio']), quote=True)}</p>"
        for person in CREATORS
    )
    comment = f"{comment_prefix}{bio} {kept} -->"
    page = ast.get_source_segment(source, fn) or ""
    name = "Chase Rose, Founder"
    close = "Every rep has a reason."
    if f">{name}</h2>" not in page or f">{close}</p>" not in page:
        raise AssertionError("the name or the close moved")
    return banner, heading, alt, name, close, paragraphs, comment


def creators_payload() -> dict:
    banner, heading, alt, name, close, paragraphs, comment = _creators_parts()
    return {
        "banner": banner,
        "heading": heading,
        "alt": alt,
        "name": name,
        "paragraphs": paragraphs,
        "close": close,
        "comment": comment,
    }


def _load_ts(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    start = text.index("= ") + 2
    end = text.rindex(" as const")
    return json.loads(text[start:end])


def _lines(payload: dict, *, creators: bool = False) -> list[str]:
    if creators:
        return [
            payload["banner"],
            payload["heading"],
            payload["alt"],
            payload["name"],
            *payload["paragraphs"],
            payload["close"],
        ]
    lines = [payload["index"], payload["heading"], payload["credit"]]
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
    """The Next copy is the Streamlit text. A diff means a sentence changed."""
    expected_about = about_payload()
    expected_creators = creators_payload()
    actual_about = _load_ts(ABOUT_TS)
    actual_creators = _load_ts(CREATORS_TS)
    diff = "".join(
        (
            _diff("about visible", _lines(expected_about), _lines(actual_about)),
            _diff("about hidden", _hidden(expected_about), _hidden(actual_about)),
            _diff("creators visible", _lines(expected_creators, creators=True), _lines(actual_creators, creators=True)),
            _diff("creators hidden", _hidden(expected_creators, creators=True), _hidden(actual_creators, creators=True)),
        )
    )
    if diff:
        raise AssertionError(diff or "the rendered copy differs")
    if actual_about != expected_about or actual_creators != expected_creators:
        raise AssertionError("the copy objects differ")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    page = app[app.index("def page_about(") : app.index("\ndef page_settings(")]
    if '<p class="rio-index rio-index-light">About</p>' not in page or "<h1>About</h1>" not in page:
        raise AssertionError("the About banner moved")
    if "about_sections(" not in page or "hidden" not in page:
        raise AssertionError("About no longer keeps the long paragraphs")
    about_view = ABOUT_VIEW.read_text(encoding="utf-8")
    creators_view = CREATORS_VIEW.read_text(encoding="utf-8")
    for token in (
        "section.title",
        "section.visible",
        "section.rows",
        "section.closing",
        "section.hidden",
        "row.label",
        "row.line",
        "ABOUT.index",
        "ABOUT.heading",
        "ABOUT.credit",
    ):
        if token not in about_view:
            raise AssertionError(token)
    for token in ("CREATORS.banner", "CREATORS.heading", "CREATORS.alt", "CREATORS.name", "CREATORS.paragraphs", "CREATORS.close", "CREATORS.comment"):
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
    if "/photos/chase-blocks" not in creators_view or "/photos/about" in creators_view:
        raise AssertionError("Creators is using the wrong photo")
    if "Photo by" in creators_view:
        raise AssertionError("Creators gained a photo credit")
    visible = "\n".join(_lines(actual_creators, creators=True))
    if "Jay Rose" in visible or "Editable placeholder" in visible or "Bio coming soon" in visible:
        raise AssertionError("a placeholder is in the visible creators text")
    if "Jay Rose" not in actual_creators["comment"] or "Editable placeholder text." not in actual_creators["comment"]:
        raise AssertionError("the hidden creators comment dropped a placeholder")
    hidden = "\n".join(_hidden(actual_about))
    shown = "\n".join(_lines(actual_about))
    if "Those calls stop once recorded spend reaches $25." not in hidden:
        raise AssertionError("the $25 sentence was dropped")
    if "$25" in shown:
        raise AssertionError("the $25 sentence is in the visible About text")


def main() -> None:
    if "--write" in sys.argv:
        _write_ts(ABOUT_TS, "ABOUT", about_payload())
        _write_ts(CREATORS_TS, "CREATORS", creators_payload())
        print("wrote about and creators copy")
        return
    test_rendered_about_and_creators_text_matches_streamlit()
    print("about creators copy ok")


if __name__ == "__main__":
    main()
