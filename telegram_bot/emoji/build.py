"""Build the NosiFit Telegram custom emoji set from ``src/*.svg``.

Outputs (100x100 transparent PNG, Telegram's static custom emoji size):
  png/color/<key>.png  brand tile + accent glyph   (pack with needs_repainting=False)
  png/mono/<key>.png   white glyph, no tile         (pack with needs_repainting=True)
  preview.html / preview.png

Uses only the stdlib plus a headless Chromium for SVG rasterisation:
  python telegram_bot/emoji/build.py [--chromium /path/to/headless_shell]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SIZE = 100
# Color tile: glyph scaled into the brand tile, stroke compensated so the
# rendered line weight matches the NosiFit mark at 20-24 px.
TILE_RADIUS = 22
TILE_SCALE = 0.70
TILE_STROKE = 11.5
MONO_STROKE = 10


def find_chromium(explicit: str | None) -> str:
    candidates = [explicit] if explicit else []
    candidates += glob.glob("/opt/pw-browsers/chromium_headless_shell-*/*/headless_shell")
    candidates += [shutil.which(n) for n in ("chromium", "chromium-browser", "google-chrome")]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    raise SystemExit("Headless Chromium not found; pass --chromium")


def glyph(key: str, stroke: float) -> str:
    svg = (ROOT / "src" / f"{key}.svg").read_text()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
    return (
        f'<g fill="none" stroke="currentColor" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-linejoin="round">{inner}</g>'
    )


def color_svg(key: str, color: str, tile: str) -> str:
    s = TILE_SCALE
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{SIZE}" height="{SIZE}">'
        f'<rect width="100" height="100" rx="{TILE_RADIUS}" fill="{tile}"/>'
        f'<g color="{color}" transform="translate(50 50) scale({s}) translate(-50 -50)">'
        f"{glyph(key, TILE_STROKE)}</g></svg>"
    )


def mono_svg(key: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{SIZE}" height="{SIZE}">'
        f'<g color="#ffffff">{glyph(key, MONO_STROKE)}</g></svg>'
    )


def render(chromium: str, html: str, out: Path, width: int, height: int) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
        page = f.name
    try:
        subprocess.run(
            [
                chromium, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                "--force-device-scale-factor=1", "--default-background-color=00000000",
                f"--window-size={width},{height}", f"--screenshot={out}", f"file://{page}",
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    finally:
        os.unlink(page)


def page(body: str) -> str:
    return f"<!doctype html><html><body style='margin:0;background:transparent'>{body}</body></html>"


def validate(path: Path) -> None:
    """Check PNG signature, 100x100, RGBA, and real transparency (stdlib only)."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path}: not a PNG"
    w, h, depth, ctype = struct.unpack(">IIBB", data[16:26])
    assert (w, h) == (SIZE, SIZE), f"{path}: {w}x{h}"
    assert depth == 8 and ctype == 6, f"{path}: expected 8-bit RGBA, got depth={depth} type={ctype}"
    idat, pos = b"", 8
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        if kind == b"IDAT":
            idat += data[pos + 8:pos + 8 + n]
        pos += 12 + n
    raw = zlib.decompress(idat)
    row = 1 + w * 4
    corner_alpha = raw[1 + 3]  # first pixel of first row (filter byte skipped)
    assert len(raw) == row * h, f"{path}: unexpected pixel data length"
    assert corner_alpha == 0, f"{path}: corner pixel is not transparent"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chromium")
    chromium = find_chromium(ap.parse_args().chromium)

    meta = json.loads((ROOT / "icons.json").read_text())
    icons, tile = meta["icons"], meta["tile"]
    for variant in ("color", "mono"):
        (ROOT / "png" / variant).mkdir(parents=True, exist_ok=True)

    for key, spec in icons.items():
        for variant, svg in (("color", color_svg(key, spec["color"], tile)), ("mono", mono_svg(key))):
            out = ROOT / "png" / variant / f"{key}.png"
            render(chromium, page(svg), out, SIZE, SIZE)
            validate(out)
            print(f"ok  {out.relative_to(ROOT)}")

    write_preview(chromium, icons)


def write_preview(chromium: str, icons: dict) -> None:
    def cells(variant: str, mono_color: str | None) -> str:
        out = []
        for key in icons:
            src = f"png/{variant}/{key}.png"
            # Telegram repaints needs_repainting emoji to the text colour; mimic it with a filter.
            tint = "" if mono_color in (None, "#ffffff") else "filter:brightness(0);"
            img = lambda px: f"<img src='{src}' width='{px}' height='{px}' style='{tint}'>"
            out.append(
                f"<div class='c'>{img(64)}<div class='s'>{img(24)}{img(20)}"
                f"<span>{key}</span></div></div>"
            )
        return "".join(out)

    themes = (("Light chat", "#ffffff", "#000000"), ("Dark chat", "#17212b", "#ffffff"))
    sections = []
    for title, bg, fg in themes:
        sections.append(
            f"<section style='background:{bg};color:{fg}'><h2>{title} · color pack</h2>"
            f"<div class='g'>{cells('color', None)}</div>"
            f"<h2>{title} · mono pack (repainted to text colour)</h2>"
            f"<div class='g'>{cells('mono', fg)}</div>"
            f"<p class='m'>{inline_sample(icons, fg)}</p></section>"
        )
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><title>NosiFit Emoji Preview</title><style>"
        "body{margin:0;font:13px system-ui,sans-serif;background:#07090d}"
        "section{padding:16px 20px}h2{font-size:13px;font-weight:600;margin:4px 0 10px;opacity:.75}"
        ".g{display:grid;grid-template-columns:repeat(11,1fr);gap:10px;margin-bottom:14px}"
        ".c{text-align:center}.s{display:flex;gap:6px;align-items:center;justify-content:center;margin-top:6px}"
        ".s span{font-size:11px;opacity:.7}.m{font-size:15px;margin:4px 0 0}"
        ".m img{vertical-align:-4px}"
        "</style></head><body>" + "".join(sections) + "</body></html>"
    )
    (ROOT / "preview.html").write_text(html)
    render(chromium, html.replace("png/", f"file://{ROOT}/png/"), ROOT / "preview.png", 1100, 660)
    print("ok  preview.html, preview.png")


def inline_sample(icons: dict, fg: str) -> str:
    e = lambda k: f"<img src='png/color/{k}.png' width='20' height='20'>"
    return (
        f"{e('calories')} 1840 / 2400 ккал &nbsp; {e('protein')} 96 г &nbsp; {e('fat')} 54 г &nbsp; "
        f"{e('carbs')} 210 г &nbsp; {e('water')} 1.5 л"
    )


if __name__ == "__main__":
    main()
