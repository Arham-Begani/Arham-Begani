"""Section headings, drawn as SVG.

GitHub strips <style> and class attributes from READMEs, so a markdown heading
can only ever look like GitHub's own headings. Drawing them as an image is the
one way to put this page's typeface and rule work on them.
"""
from __future__ import annotations

from .svgkit import Theme, svg, text_path, text_width

WIDTH = 880
HEIGHT = 34
SIZE = 17
TRACKING = 2.4


def heading(label: str, theme: Theme, *, width: int = WIDTH) -> str:
    baseline = 22.0
    w = text_width(label, SIZE, "ExtraBold", TRACKING) - TRACKING
    body = [text_path(label, size=SIZE, x=0, y=baseline, weight="ExtraBold",
                      fill=theme.ink, tracking=TRACKING)]
    rule_x = w + 18
    body.append(
        f'<rect x="{rule_x:.1f}" y="{baseline - 5:.1f}" width="0" height="1" fill="{theme.dim}">'
        f'<animate attributeName="width" from="0" to="{width - rule_x:.1f}" '
        f'begin="0.15s" dur="0.7s" calcMode="spline" keySplines="0.16 1 0.3 1" fill="freeze"/>'
        f"</rect>"
    )
    return svg(width, HEIGHT, "".join(body), title=label)
