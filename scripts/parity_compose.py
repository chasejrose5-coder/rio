"""Place one Streamlit shot beside one Next shot, and diff the visible text.

The two screenshots are each a single full-page capture. This only sets
them next to each other. It does not scroll or stitch.
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CHROME = {
    "deploy",
    "rerun",
    "stop",
    "made with streamlit",
    "menu",
}


def lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    found = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = " ".join(raw.split()).strip()
        if not text or text.casefold() in CHROME:
            continue
        found.append(text)
    return found


def compose(left_path: Path, right_path: Path, dest: Path) -> None:
    left = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB")
    label = 36
    gap = 16
    width = left.width + right.width + gap
    height = label + max(left.height, right.height)
    canvas = Image.new("RGB", (width, height), (244, 241, 236))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((12, 10), "Streamlit", fill=(18, 17, 16), font=font)
    draw.text((left.width + gap + 12, 10), "Next", fill=(18, 17, 16), font=font)
    canvas.paste(left, (0, label))
    canvas.paste(right, (left.width + gap, label))
    canvas.save(dest, quality=68, optimize=True)


def main() -> None:
    out = Path(sys.argv[1])
    text = out / "text"
    sides = out / "side"
    sides.mkdir(exist_ok=True)
    names = sorted(path.name[len("next-") : -len(".png")] for path in out.glob("next-*.png"))
    summary = []
    for name in names:
        left = out / f"stream-{name}.png"
        right = out / f"next-{name}.png"
        if not left.is_file():
            summary.append(f"{name}\tMISSING streamlit shot")
            continue
        compose(left, right, sides / f"{name}.jpg")
        stream_lines = lines(text / f"stream-{name}.txt")
        next_lines = lines(text / f"next-{name}.txt")
        diff = "".join(
            difflib.unified_diff(
                stream_lines,
                next_lines,
                fromfile=f"streamlit/{name}",
                tofile=f"next/{name}",
                lineterm="\n",
            )
        )
        (text / f"{name}.diff").write_text(diff, encoding="utf-8")
        hidden_diff = "".join(
            difflib.unified_diff(
                lines(text / f"stream-{name}.hidden.txt"),
                lines(text / f"next-{name}.hidden.txt"),
                fromfile=f"streamlit-hidden/{name}",
                tofile=f"next-hidden/{name}",
                lineterm="\n",
            )
        )
        (text / f"{name}.hidden.diff").write_text(hidden_diff, encoding="utf-8")
        summary.append(f"{name}\tvisible={len(diff.splitlines())}\thidden={len(hidden_diff.splitlines())}")
    (out / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
