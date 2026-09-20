"""Shared SVG plumbing: themes, font-to-path conversion, tiny helpers.

Everything on this page is drawn rather than typeset, because GitHub renders
README images in "secure static mode": no scripts, no external references, and
no CSS from the surrounding page. Declarative SMIL animation survives, and so
do <path> elements -- so we convert text to outlines and animate with <animate>.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# Fallback stack used only for the bulk character grids (portrait, heatmap),
# where outlining every glyph would bloat the file. Rows are pinned with
# textLength so the grid stays aligned whatever the viewer's monospace face is.
MONO_STACK = "ui-monospace,'SFMono-Regular','JetBrains Mono',Menlo,Consolas,'Liberation Mono',monospace"


@dataclass(frozen=True)
class Theme:
    name: str
    ink: str        # primary text
    muted: str      # secondary text
    dim: str        # rules, axis labels, empty cells
    accent: str     # links, highlights
    glow: str       # strongest emphasis (big numbers)


DARK = Theme("dark", ink="#e6edf3", muted="#8b949e", dim="#30363d", accent="#58a6ff", glow="#ffffff")
LIGHT = Theme("light", ink="#1f2328", muted="#59636e", dim="#d1d9e0", accent="#0969da", glow="#000000")
THEMES = (DARK, LIGHT)


# --------------------------------------------------------------------------- font

def _ntos(v: float) -> str:
    """Path coordinates, rounded to whole font units.

    Outlines are emitted in font units and scaled by size/unitsPerEm at draw
    time, so one unit is 1/1000 em -- 0.06px at the largest size on this page.
    A decimal place is therefore 0.006px of detail nobody can see, bought at
    two bytes per number, and there are tens of thousands of numbers here.
    """
    n = round(v)
    return "0" if n == 0 else f"{n:d}"


def hold(attr: str, value: str) -> str:
    """Pin `attr` to its pre-animation value at t=0.

    The elements on this page are written with their *finished* value in the
    static attribute, so a renderer that never runs the animation still shows
    the completed drawing. That covers the window before the SMIL clock starts
    and any viewer that strips animation. This <set> is what puts them back to
    the starting value when the clock does run; the delayed <animate> that
    follows begins later, so it takes priority from its own begin onward.
    """
    return f'<set attributeName="{attr}" to="{value}" begin="0s"/>'


@lru_cache(maxsize=8)
def _font(weight: str) -> tuple[TTFont, object, int]:
    path = FONT_DIR / f"JetBrainsMono-{weight}.ttf"
    if not path.exists():
        raise FileNotFoundError(
            f"missing {path}. Run scripts/fetch_fonts.sh, or drop JetBrains Mono TTFs in assets/fonts/."
        )
    font = TTFont(str(path), lazy=True)
    return font, font.getGlyphSet(), font["head"].unitsPerEm


def advance_ratio(weight: str = "Regular") -> float:
    """Width of one character as a fraction of the font size (0.6 for JBM)."""
    font, glyphs, upm = _font(weight)
    name = font.getBestCmap().get(ord("0"))
    return font["hmtx"][name][0] / upm


def text_width(s: str, size: float, weight: str = "Regular", tracking: float = 0.0) -> float:
    return len(s) * (advance_ratio(weight) * size + tracking)


def text_path(
    s: str,
    *,
    size: float,
    x: float = 0.0,
    y: float = 0.0,
    weight: str = "Regular",
    fill: str = "#fff",
    tracking: float = 0.0,
    opacity: float | None = None,
    extra: str = "",
) -> str:
    """Render a string as a single outlined <path>.

    y is the baseline. Font units are y-up, SVG is y-down, hence scale(s, -s).
    """
    font, glyphs, upm = _font(weight)
    cmap = font.getBestCmap()
    scale = size / upm
    step = advance_ratio(weight) * size + tracking
    d: list[str] = []
    for i, ch in enumerate(s):
        name = cmap.get(ord(ch))
        if name is None or ch == " ":
            continue
        pen = SVGPathPen(glyphs, ntos=_ntos)
        # Offset in font units so a single transform covers the whole run.
        tp = TransformPen(pen, (1, 0, 0, 1, (i * step) / scale, 0))
        glyphs[name].draw(tp)
        seg = pen.getCommands()
        if seg:
            d.append(seg)
    if not d:
        return ""
    op = "" if opacity is None else f' opacity="{opacity}"'
    return (
        f'<g transform="translate({x:.2f} {y:.2f}) scale({scale:.6f} {-scale:.6f})">'
        f'<path fill="{fill}"{op} d="{"".join(d)}"{extra}/></g>'
    )


# --------------------------------------------------------------------------- svg

def svg(width: float, height: float, body: str, *, title: str = "") -> str:
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
        f'aria-label="{escape(title)}" font-kerning="none">'
    )
    t = f"<title>{escape(title)}</title>" if title else ""
    return f"{head}{t}{body}</svg>\n"


def grid_text(
    rows: list[str],
    *,
    x: float,
    y: float,
    size: float,
    line_height: float,
    cell: float,
    fill: str,
    opacity: float = 1.0,
    weight: int = 400,
    adjust: str = "spacing",
) -> str:
    """A block of monospace rows, each pinned to an exact width.

    textLength + lengthAdjust="spacing" makes the grid survive font substitution:
    whatever face the viewer has, row N still ends where we said it would.
    """
    out = []
    for i, row in enumerate(rows):
        if not row.strip():
            continue
        body = escape(row.rstrip())
        if not body:
            continue
        out.append(
            f'<text x="{x:.2f}" y="{y + i * line_height:.2f}" '
            f'textLength="{len(row.rstrip()) * cell:.2f}" lengthAdjust="{adjust}" '
            f'xml:space="preserve">{body}</text>'
        )
    return (
        f'<g font-family="{MONO_STACK}" font-size="{size:.2f}" font-weight="{weight}" '
        f'fill="{fill}" opacity="{opacity}">{"".join(out)}</g>'
    )


def digest(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode())
    return h.hexdigest()[:8]
