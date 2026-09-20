"""A photo, pushed through a character ramp, revealed by a SMIL wipe.

The reveal is a clipPath whose rect grows downward, so the picture draws itself
top of head first. One <animate> element does the whole thing -- no script,
which matters because GitHub renders README images with scripting disabled.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from .svgkit import Theme, grid_text, svg

# Ramps run sparse -> dense. Index 0 must be a space.
RAMPS = {
    # Measured, not guessed: each glyph's ink coverage was rasterised in a
    # monospace face and the ramp picked so the steps are perceptually even.
    "even": " `-,~_!r|ljJIkSA6D@M",
    "fine": " .,:;irsXA253hMHGS#9B&@",
    "classic": " .:-=+*#%@",
    "blocks": " ░▒▓█",
    "dots": " .·:•▪■█",
}

CELL_ASPECT = 0.6 / 1.08  # character advance / line height


def _prepare(path: Path, *, gamma: float, vignette: float, local: float = 1.2) -> Image.Image:
    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        flat = Image.new("RGBA", img.size, (255, 255, 255, 255))
        flat.alpha_composite(img)
        img = flat
    img = img.convert("L")
    img = ImageOps.autocontrast(img, cutoff=(1, 1))

    a = np.asarray(img, dtype=np.float32) / 255.0
    if local > 0:
        # Local contrast. A ramp only has ~20 tones, and in most portraits the
        # face and the background sit within a few tones of each other -- so
        # global levels flatten the subject into the backdrop. Subtracting a
        # wide blur re-separates them the way CLAHE would.
        radius = max(img.size) / 9.0
        blur = np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0
        a = np.clip(a + local * (a - blur), 0, 1)
        a = (a - a.min()) / max(1e-6, a.max() - a.min())

    img = Image.fromarray((a * 255).astype(np.uint8), "L")
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=90, threshold=2))
    img = ImageEnhance.Contrast(img).enhance(1.15)
    a = np.asarray(img, dtype=np.float32) / 255.0
    if gamma != 1.0:
        a = np.clip(a, 0, 1) ** gamma
    if vignette > 0:
        h, w = a.shape
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        falloff = np.clip(1.0 - vignette * np.clip(r - 0.55, 0, None) / 0.45, 0, 1)
        a = a * falloff + (1 - falloff) * float(np.median(a[:, :3]))
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "L")


def sample(path: Path, cols: int, *, gamma: float = 1.0, vignette: float = 0.0,
           local: float = 1.2) -> np.ndarray:
    """Return a rows x cols float array of luminance in 0..1."""
    img = _prepare(path, gamma=gamma, vignette=vignette, local=local)
    w, h = img.size
    rows = max(1, int(round(cols * (h / w) * CELL_ASPECT)))
    small = img.resize((cols, rows), Image.Resampling.LANCZOS)
    return np.asarray(small, dtype=np.float32) / 255.0


def to_rows(lum: np.ndarray, ramp: str, *, invert: bool, weight: float = 1.0) -> list[str]:
    """Map luminance onto the ramp.

    `invert` puts the dense glyphs where the picture is *dark*, so the ASCII
    follows the subject's own ink. `weight` above 1 pulls the mid-tones down,
    which stops a large black mass (a suit, a jacket) from flooding the frame.
    """
    v = 1.0 - lum if invert else lum
    lo, hi = float(v.min()), float(v.max())
    v = (v - lo) / (hi - lo) if hi > lo else v * 0
    if weight != 1.0:
        v = np.clip(v, 0, 1) ** weight
    idx = np.clip((v * (len(ramp) - 1) + 0.5).astype(int), 0, len(ramp) - 1)
    return ["".join(ramp[i] for i in row) for row in idx]


def render(
    lum: np.ndarray,
    theme: Theme,
    *,
    width: int = 460,
    ramp: str = "even",
    polarity: str = "ink",
    weight: float = 1.0,
    duration: float = 2.2,
    alt: str = "ASCII portrait",
) -> str:
    chars = RAMPS.get(ramp, ramp)
    rows_n, cols = lum.shape
    size = width / (cols * 0.6)
    cell = size * 0.6
    line = size * 1.08
    height = rows_n * line + size * 0.4
    baseline = size * 0.85

    # "ink"   -- dense where the picture is dark, in both themes: the ASCII
    #            follows the drawing's own ink. Right for artwork, line work,
    #            and anything shot against a light background.
    # "light" -- dense where the picture is bright: right for a lit subject
    #            against a dark background.
    # "theme" -- follow the page instead of the picture.
    invert = {"ink": True, "light": False}.get(polarity, theme.name == "light")
    rows = to_rows(lum, chars, invert=invert, weight=weight)

    body = [
        f'<defs><clipPath id="wipe"><rect x="0" y="0" width="{width}" height="0">'
        f'<animate attributeName="height" values="0;{height:.1f}" dur="{duration}s" '
        f'calcMode="spline" keySplines="0.22 0.61 0.36 1" fill="freeze"/>'
        f"</rect></clipPath></defs>",
        '<g clip-path="url(#wipe)">',
        grid_text(rows, x=0, y=baseline, size=size, line_height=line, cell=cell,
                  fill=theme.ink, opacity=0.92),
        "</g>",
        # the scan edge, which fades out once the wipe lands
        f'<rect x="0" y="-1.5" width="{width}" height="1.5" fill="{theme.accent}" opacity="0.55">'
        f'<animate attributeName="y" values="-1.5;{height:.1f}" dur="{duration}s" '
        f'calcMode="spline" keySplines="0.22 0.61 0.36 1" fill="freeze"/>'
        f'<animate attributeName="opacity" values="0;0.55;0.55;0" '
        f'keyTimes="0;0.06;0.9;1" dur="{duration}s" fill="freeze"/>'
        f"</rect>",
    ]
    return svg(width, height, "".join(body), title=alt)
